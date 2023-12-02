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

    def __init__(self, redis_handler: RedisHandler, redeems: dict[str,
                 Callable], twitch_handler: TwitchHandler) -> None:
        self.redis_handler = redis_handler
        self.redeems = redeems
        self.twitch_handler = twitch_handler

        self.local_redeems = []

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
            local_path = pathlib.Path(local_file)
            local_module_path = str(local_path).replace('/', '.').replace('.py', '')

            redeem = importlib.import_module(local_module_path)

            redeem_parsed = Redeem(
                title=redeem.title,
                description=redeem.description,
                cost=redeem.cost,
                enabled=redeem.enabled,
                handler=redeem.handle
            )

            self.local_redeems.append(redeem_parsed)

        await self.register_redeems()

        pubsub = await self.redis_handler.get_pubsub()

        for redeem in self.local_redeems:
            channel_name = f"redeems:{redeem.title}"
            logger.debug(f"registered channel {channel_name}")
            await pubsub.subscribe(channel_name)

        await self.consumer(pubsub)

    async def stop(self):
        ...

    async def register_redeems(self):
        remote_redeems: list[CustomReward] = await self.twitch_handler.get_existing_custom_redeems()  # exisiting custom_rewards in twitch account

        local_redeems_names = [r.title for r in self.local_redeems]
        remote_redeems_names = [r.title for r in remote_redeems]

        for redeem in self.local_redeems:
            if redeem.title not in remote_redeems_names:
                logger.info(f"local redeem {redeem.title} does not exist remotely. creating...")

                await self.twitch_handler.create_custom_redeem(redeem)
                continue

            remote_redeem = [r for r in remote_redeems if r.title ==
            redeem.title][0]

            if (
                    remote_redeem.prompt != redeem.description or
                    remote_redeem.cost != redeem.cost
            ):
                logger.info(f"updating redeem {redeem.title}")

                await self.twitch_handler.update_redeem(
                    remote_redeem.id,
                    redeem
                )

    async def consumer(self, pubsub: PubSub):
        logger.info("starting consumer")

        current_redeem_names = [r.title for r in self.local_redeems]
        logger.debug(current_redeem_names)

        while True:
            try:
                async with async_timeout.timeout(2):
                    message = await pubsub.get_message(ignore_subscribe_messages=True)
                    if message is None:
                        await asyncio.sleep(0.01)
                        continue

                    redeem_name = message['channel'].decode().split(':')[1]
                    logger.debug(f"message from {redeem_name}")
                    logger.debug(f"details: {message}")

                    if redeem_name in current_redeem_names:
                        redeem = [r for r in self.local_redeems if r.title == redeem_name][0]

                        await redeem.handler()

                    await asyncio.sleep(0.01)
            except asyncio.TimeoutError:
                pass
