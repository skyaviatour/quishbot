# 1 trigger start filter on current scene
## a: get current scene name LISTO
## b: get list of filters, and get the start one## a: get current scene name LISTO
## c: activate START filter on current scene LISTO
## d: play squeaky toy sound
# 2 read redeem from twitch chat and call #1 LISTO
import asyncio
import logging
import sys

from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticationStorageHelper
from quishbot.config import APP_ID, APP_SECRET, LOG_LEVEL, TARGET_SCOPES
from quishbot.redeems import RedeemHandler
from quishbot.redishandler import RedisHandler
from quishbot.redeem_commands import squish

from quishbot.twitch import TwitchHandler


logging.basicConfig(stream=sys.stdout, level=getattr(logging, LOG_LEVEL))


async def main():
    logger = logging.getLogger()

    redeems = {
        'squish': squish.handle
    }

    twitch = await Twitch(APP_ID, APP_SECRET)
    auth_helper = UserAuthenticationStorageHelper(twitch, TARGET_SCOPES)
    await auth_helper.bind()

    redis_handler = RedisHandler("redis://localhost", logger=logger)
    twitch_handler = TwitchHandler(instance=twitch, redis_handler=redis_handler, logger=logger)
    redeems_handler = RedeemHandler(redis_handler=redis_handler, redeems=redeems, logger=logger)

    await asyncio.gather(
        asyncio.create_task(redis_handler.start()),
        asyncio.create_task(redeems_handler.start()),
        asyncio.create_task(twitch_handler.start())
    )

    logger.info("done??????????")


if __name__ == '__main__':
    asyncio.run(main())
