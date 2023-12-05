class GenericQueue:
    async def put_message(self, queue_name, value):
        raise NotImplementedError

    def get_message(self, queue_name):
        raise NotImplementedError

    async def register_queue(self, queue_name):
        raise NotImplementedError
