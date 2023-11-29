import asyncio
import logging
from typing import Callable
import async_timeout

from redis.asyncio.client import PubSub
from quishbot.redishandler import RedisHandler


logger = logging.getLogger(__name__)


class RedeemHandler:
    redis_handler: RedisHandler
    redeems: dict[str, Callable]

    def __init__(self, redis_handler: RedisHandler, redeems: dict[str, Callable]) -> None:
        self.redis_handler = redis_handler
        self.redeems = redeems

    async def start(self):
        logger.info("handling redeem channels")

        pubsub = await self.redis_handler.get_pubsub()

        for redeem in self.redeems:
            channel_name = f"redeems:{redeem}"
            await pubsub.subscribe(channel_name)

        await self.consumer(pubsub)

    async def stop(self):
        ...

    async def consumer(self, pubsub: PubSub):
        logger.info("starting consumer")

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
