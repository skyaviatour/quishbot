import asyncio
import logging
import sys

from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticationStorageHelper
from quishbot.config import APP_ID, APP_SECRET, LOG_LEVEL, TARGET_SCOPES
from quishbot.queues.local import LocalQueue
from quishbot.redeems import RedeemHandler
from quishbot.redeem_commands import squish

from quishbot.twitch import TwitchHandler


logging.basicConfig(
    stream=sys.stdout,
    level=getattr(logging, LOG_LEVEL),
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
)


async def main():
    redeems = {
        'squish': squish.handle
    }

    twitch = await Twitch(APP_ID, APP_SECRET)
    auth_helper = UserAuthenticationStorageHelper(twitch, TARGET_SCOPES)
    await auth_helper.bind()

    # redis_handler = RedisHandler("redis://localhost")
    local_queue = LocalQueue()
    twitch_handler = TwitchHandler(instance=twitch, queue=local_queue)
    redeems_handler = RedeemHandler(queue=local_queue,
                                    redeems=redeems, twitch_handler=twitch_handler)

    await asyncio.gather(
        # asyncio.create_task(redis_handler.start()),
        asyncio.create_task(twitch_handler.start()),
        asyncio.create_task(redeems_handler.start()),
        asyncio.create_task(redeems_handler.start_refund_watcher())
    )


if __name__ == '__main__':
    asyncio.run(main())
