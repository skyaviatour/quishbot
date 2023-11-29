import asyncio
from logging import Logger
from typing import Callable
import async_timeout

from redis.asyncio.client import PubSub
from quishbot.redishandler import RedisHandler


class RedeemHandler:
    redis_handler: RedisHandler
    redeems: dict[str, Callable]
    logger: Logger

    def __init__(self, redis_handler: RedisHandler, redeems: dict[str, Callable], logger: Logger) -> None:
        self.redis_handler = redis_handler
        self.redeems = redeems
        self.logger = logger

    async def start(self):
        self.logger.info("handling redeem channels")

        pubsub = await self.redis_handler.get_pubsub()

        for redeem in self.redeems:
            channel_name = f"redeems:{redeem}"
            await pubsub.subscribe(channel_name)

        await self.consumer(pubsub)

    async def stop(self):
        ...

    async def consumer(self, pubsub: PubSub):
        self.logger.info("starting consumer")

        while True:
            try:
                async with async_timeout.timeout(2):
                    message = await pubsub.get_message(ignore_subscribe_messages=True)
                    if message is None:
                        await asyncio.sleep(0.01)
                        continue

                    if message['data'].decode() == 'go':
                        redeem = message['channel'].decode().split(':')[1]
                        await self.redeems[redeem]()

                    await asyncio.sleep(0.01)
            except asyncio.TimeoutError:
                pass
