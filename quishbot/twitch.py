from logging import Logger
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.helper import first
from twitchAPI.twitch import Twitch
from quishbot.config import SQUISH_REDEEM_ID

from quishbot.redishandler import RedisHandler


class TwitchHandler:
    instance: Twitch
    redis_handler: RedisHandler
    logger: Logger
    event_sub_ws: EventSubWebsocket

    def __init__(self, instance: Twitch, redis_handler: RedisHandler, logger: Logger) -> None:
        self.instance = instance
        self.redis_handler = redis_handler
        self.logger = logger

    async def start(self):
        me = await first(self.instance.get_users())

        if not me:
            exit(1)

        self.event_sub_ws = EventSubWebsocket(self.instance)
        self.event_sub_ws.start()

        await self.event_sub_ws.listen_channel_points_custom_reward_redemption_add(me.id, self.handle_squish_redeem, reward_id=SQUISH_REDEEM_ID)

        self.logger.info("ready to accept redeems")

    async def stop(self):
        ...

    async def handle_squish_redeem(self, _):
        await self.redis_handler.publish("redeems:squish", "go")
