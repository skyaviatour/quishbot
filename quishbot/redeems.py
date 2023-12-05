import asyncio
import logging
from typing import Callable
import pathlib
import importlib
import os

from twitchAPI.object.api import CustomReward
from quishbot.queues.generic import GenericQueue
from quishbot.twitch import TwitchHandler
from quishbot.types.redeem import Redeem


logger = logging.getLogger(__name__)


class RedeemHandler:
    LOCAL_REDEEMS_DIR = "redeem_commands"
    queue: GenericQueue
    twitch_handler: TwitchHandler
    redeems: dict[str, Callable]

    local_redeems: list[Redeem]
    registered_redeems: dict
    running: bool

    def __init__(self, queue: GenericQueue, redeems: dict[str,
                 Callable], twitch_handler: TwitchHandler) -> None:
        self.queue = queue
        self.redeems = redeems
        self.twitch_handler = twitch_handler

        self.local_redeems = []
        self.registered_redeems = {}

        self.running = True

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

        for redeem in self.local_redeems:
            if redeem.queue_name is None:
                continue

            channel_name = f"redeems:{redeem.queue_name}"
            self.twitch_handler.register_redeem_queue(redeem.title, redeem.queue_name)
            logger.info(f"registered channel {channel_name}")
            # await pubsub.subscribe(channel_name)
            queue_name = f"redeems:{redeem.queue_name}"
            await self.queue.register_queue(queue_name)

        await self.start_consumer()

    async def stop(self):
        self.running = False

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

        while self.running:
            for redeem in self.registered_redeems.values():
                await self.twitch_handler.refund_pending_redeems(redeem['id'])
            # check every 5 minutes
            # i have no idea about twitch api rate limits, so just play it safe
            await asyncio.sleep(60 * 5)

    async def start_consumer(self):
        logger.info("starting consumer")

        while self.running:
            for redeem in self.local_redeems:
                if redeem.queue_name is None:
                    continue

                queue_name = f"redeems:{redeem.queue_name}"
                reward_id = self.queue.get_message(queue_name)
                if reward_id is None:
                    continue

                logger.debug(f"got message {reward_id} from {queue_name}")

                await self.consume(redeem, reward_id)

            await asyncio.sleep(0.1)

    async def consume(self, redeem, reward_id):
        logger.debug(f"message from {redeem.queue_name}")
        logger.debug(f"details: {reward_id}")

        redeem_twitch_id = self.registered_redeems[redeem.title]['id']

        try:
            logger.debug("running redeem handler")
            await redeem.handler()
            logger.debug("redeem OK, confirming")
            await self.twitch_handler.confirm_custom_redeem(redeem_twitch_id, reward_id)
        except Exception as e:
            logger.error(f"redeem {redeem.title} failed: ")
            logger.error(e)
