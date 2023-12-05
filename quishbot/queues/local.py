from asyncio import Queue, QueueEmpty
import logging
from quishbot.queues.generic import GenericQueue


logger = logging.getLogger(__name__)


class LocalQueue(GenericQueue):
    queues: dict[str, Queue]

    def __init__(self) -> None:
        self.queues = {}

    async def put_message(self, queue_name, value):
        logger.debug(f"pushing to {queue_name}: {value}")
        queue = self.queues[queue_name]

        await queue.put(value)

        logger.debug(f"pushed to {queue_name}: {value}")

    def get_message(self, queue_name) -> str | None:
        queue = self.queues[queue_name]

        try:
            msg = queue.get_nowait()
            logger.debug(f"got from {queue_name}: {msg}")
            return msg
        except QueueEmpty:
            return None

    async def register_queue(self, queue_name):
        logger.debug(f"registered {queue_name}")

        queue = Queue()

        self.queues[queue_name] = queue
