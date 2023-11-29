from logging import Logger
import redis.asyncio as redis
from redis.asyncio.client import PubSub


class RedisHandler:
    host: str
    client: redis.Redis
    logger: Logger
    pubsub: PubSub

    def __init__(self, host: str, logger: Logger) -> None:
        self.host = host
        self.logger = logger

    async def start(self):
        self.logger.info("starting redis handler")
        self.client = redis.from_url(self.host)
        self.pubsub = self.client.pubsub()

    async def stop(self):
        await self.client.aclose()

    async def get_pubsub(self):
        return self.pubsub

    async def publish(self, channel: str, message: str):
        await self.client.publish(channel, message)
