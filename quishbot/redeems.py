import asyncio
import logging
from typing import Callable
import async_timeout
import pathlib
import importlib
import os

from redis.asyncio.client import PubSub
from twitchAPI.object.api import CustomReward
from quishbot.redishandler import RedisHandler
from quishbot.twitch import TwitchHandler
from quishbot.types.redeem import Redeem


logger = logging.getLogger(__name__)


class RedeemHandler:
    LOCAL_REDEEMS_DIR = "redeem_commands"
    redis_handler: RedisHandler
    twitch_handler: TwitchHandler
    redeems: dict[str, Callable]

    local_redeems: list[Redeem]
    registered_redeems: dict

    def __init__(self, redis_handler: RedisHandler, redeems: dict[str,
                 Callable], twitch_handler: TwitchHandler) -> None:
        self.redis_handler = redis_handler
        self.redeems = redeems
        self.twitch_handler = twitch_handler

        self.local_redeems = []
        self.registered_redeems = {}

    async def start(self):
        logger.info("handling redeem channels")

        root_path = pathlib.Path(os.getcwd()).name
        local_redeem_dir_path = pathlib.Path(root_path) / self.LOCAL_REDEEMS_DIR

        local_redeem_files = [
            local_file for local_file in
            local_redeem_dir_path.iterdir() if not
            local_file.name.startswith('__')
        ]

        for local_file in local_redeem_files:
            local_module_path = str(local_file).replace('/', '.').replace('.py', '')

            redeem = importlib.import_module(local_module_path)

            redeem_parsed = Redeem(
                title=redeem.title,
                description=redeem.description,
                cost=redeem.cost,
                enabled=redeem.enabled,
                queue_name=redeem.queue_name,
                handler=redeem.handle
            )

            self.local_redeems.append(redeem_parsed)

        await self.register_redeems()

        pubsub = await self.redis_handler.get_pubsub()

        for redeem in self.local_redeems:
            if redeem.queue_name is None:
                continue

            channel_name = f"redeems:{redeem.queue_name}"
            self.twitch_handler.register_redeem_queue(redeem.title, redeem.queue_name)
            logger.info(f"registered channel {channel_name}")
            await pubsub.subscribe(channel_name)

        await self.start_consumer(pubsub)

    async def stop(self):
        ...

    async def register_redeems(self):
        # exisiting custom_rewards in twitch account
        remote_redeems: list[CustomReward] = await self.twitch_handler.get_existing_custom_redeems()
        remote_redeems_names = [r.title for r in remote_redeems]

        for redeem in self.local_redeems:
            if redeem.title not in remote_redeems_names:
                logger.info(f"local redeem {redeem.title} does not exist remotely. creating...")

                new_remote_redeem = await self.twitch_handler.create_custom_redeem(redeem)
                remote_redeems.append(new_remote_redeem)

            remote_redeem = [r for r in remote_redeems if r.title == redeem.title][0]
            self.registered_redeems[remote_redeem.title] = {
                'id': remote_redeem.id,
                'queue_name': redeem.queue_name
            }

            if (
                    remote_redeem.prompt != redeem.description or
                    remote_redeem.cost != redeem.cost
            ):
                logger.info(f"updating redeem {redeem.title}")

                await self.twitch_handler.update_redeem(
                    remote_redeem.id,
                    redeem
                )

    async def start_refund_watcher(self):
        # check every minute and refund any unfulfilled redeems that we control
        logger.info("starting redeem refund watcher")

        while True:
            for redeem in self.registered_redeems.values():
                await self.twitch_handler.refund_pending_redeems(redeem['id'])
            # check every 5 minutes
            # i have no idea about twitch api rate limits, so just play it safe
            await asyncio.sleep(60 * 5)

    async def start_consumer(self, pubsub: PubSub):
        logger.info("starting consumer")

        current_redeem_names = [r.title for r in self.local_redeems]
        logger.debug(current_redeem_names)

        while True:
            try:
                async with async_timeout.timeout(5):
                    message = await pubsub.get_message(ignore_subscribe_messages=True)
                    if message is None:
                        await asyncio.sleep(0.01)
                        continue

                    await self.consume(message)

                    await asyncio.sleep(0.01)
            except asyncio.TimeoutError:
                pass

    async def consume(self, message):
        current_redeem_queues = [r.queue_name for r in self.local_redeems]
        redeem_queue = message['channel'].decode().split(':')[1]
        redeem_reward_id = message['data'].decode()
        logger.debug(f"message from {redeem_queue}")
        logger.debug(f"details: {message}")

        if redeem_queue in current_redeem_queues:
            redeem = [r for r in self.local_redeems if r.queue_name == redeem_queue][0]
            redeem_id = self.registered_redeems[redeem.title]['id']

            try:
                logger.debug("running redeem handler")
                await redeem.handler()
                logger.debug("redeem OK, confirming")
                await self.twitch_handler.confirm_custom_redeem(redeem_id, redeem_reward_id)
            except Exception as e:
                logger.error(f"redeem {redeem.title} failed: ")
                logger.error(e)
