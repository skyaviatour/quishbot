# 1 trigger start filter on current scene
## a: get current scene name LISTO
## b: get list of filters, and get the start one## a: get current scene name LISTO
## c: activate START filter on current scene LISTO
## d: play squeaky toy sound
# 2 read redeem from twitch chat and call #1 LISTO
from redis import asyncio as aioredis
import async_timeout
import asyncio
import logging
import sys

import config
import obs

from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.helper import first
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator


logger = logging.basicConfig(stream=sys.stdout, level=getattr(logging, config.LOG_LEVEL))


async def start_squish_effect():
    conn = obs.get_connection()

    scenes = conn.get_scene_list()
    if not scenes:
        exit(2)

    current_scene_name = scenes.current_program_scene_name  # type: ignore

    # The redeem takes around 600ms + 800ms + 300ms to execute, but toggling the
    # filter returns instantly. So we delay the end of the function to not
    # overconsume messages
    conn.set_source_filter_enabled(current_scene_name, config.SQUISH_FILTER_NAME, True)
    await asyncio.sleep(2)


async def on_redeem(_):
    redis = aioredis.from_url("redis://localhost")

    print("pushing to redis")
    await redis.publish("redeems:squish", "go")


async def redeems_consumer(channel: aioredis.client.PubSub):  # type: ignore
    logging.info("starting redis consumer")
    while True:
        try:
            async with async_timeout.timeout(2):
                message = await channel.get_message(ignore_subscribe_messages=True)
                if message is not None:
                    if message['data'].decode() == 'go':
                        await start_squish_effect()
                await asyncio.sleep(0.01)
        except asyncio.TimeoutError:
            pass


async def run_redeems_consumer():
    redis = aioredis.from_url("redis://localhost")

    pubsub = redis.pubsub()
    await pubsub.subscribe("redeems:squish")

    future = asyncio.create_task(redeems_consumer(pubsub))

    await future


async def run_twitch():
    twitch: Twitch = await Twitch(config.APP_ID, config.APP_SECRET)
    auth = UserAuthenticator(twitch, config.TARGET_SCOPES, url=config.CALLBACK_URL)
    auth.port = 5000

    token, refresh_token = await auth.authenticate()  # type: ignore

    await twitch.set_user_authentication(token, config.TARGET_SCOPES, refresh_token)

    me = await first(twitch.get_users())

    if not me:
        exit(1)

    es = EventSubWebsocket(twitch)
    es.start()

    # TODO: handling redeems via API requires them ALSO being created via API
    # Define a "redeems" module, and setup a "on_startup" block to create them
    # if they don't exist
    ##  my_redeems = await twitch.get_custom_reward(me.id)
    ##  for redeem in my_redeems:
    ##      print(redeem.to_dict())
    ##      if not redeem.is_enabled:
    ##          await twitch.update_custom_reward(me.id, redeem.id, is_enabled=True)

    await es.listen_channel_points_custom_reward_redemption_add(
        me.id,
        on_redeem,
        reward_id=config.SQUISH_REDEEM_ID
    )

    logging.info("ready to accept redeems")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    tasks = asyncio.gather(
        run_twitch(),
        run_redeems_consumer()
    )
    try:
        loop.run_until_complete(tasks)
    except KeyboardInterrupt:
        logging.info("exiting...")
        tasks.cancel()
        loop.close()
