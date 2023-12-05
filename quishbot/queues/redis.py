from quishbot.queues.generic import Queue


class RedisQueue(Queue):
    def __init__(self) -> None:
        pass

    def put_message(self, queue, value):
        pass

    def get_message(self, queue):
        pass
