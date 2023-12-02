import logging
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.helper import first
from twitchAPI.object.eventsub import ChannelPointsCustomRewardRedemptionAddEvent
from twitchAPI.twitch import CustomReward, Twitch
from quishbot.config import SQUISH_REDEEM_ID

from quishbot.redishandler import RedisHandler
from quishbot.types.redeem import Redeem


logger = logging.getLogger(__name__)


class TwitchHandler:
    instance: Twitch
    redis_handler: RedisHandler
    event_sub_ws: EventSubWebsocket

    my_id: str

    def __init__(self, instance: Twitch, redis_handler: RedisHandler) -> None:
        self.instance = instance
        self.redis_handler = redis_handler

    async def start(self):
        me = await first(self.instance.get_users())

        if not me:
            exit(1)

        self.my_id = me.id

        self.event_sub_ws = EventSubWebsocket(self.instance)
        self.event_sub_ws.start()

        await self.event_sub_ws.listen_channel_points_custom_reward_redemption_add(
            me.id,
            self.handle_redeem_queue
        )

        logger.info("ready to accept redeems")

    async def stop(self):
        ...

    async def _get_my_id(self):
        me = await first(self.instance.get_users())

        if not me:
            exit(255)

        return me.id

    async def handle_redeem_queue(self, data: ChannelPointsCustomRewardRedemptionAddEvent):
        await self.redis_handler.publish(f"redeems:{data.event.reward.title}", "go")

    async def update_redeem(self, reward_id: str, data: Redeem):
        my_id = await self._get_my_id()

        await self.instance.update_custom_reward(
            my_id,
            reward_id,
            prompt=data.description,
            cost=data.cost,
            is_enabled=data.enabled
        )

    async def get_existing_custom_redeems(self) -> list[CustomReward]:
        my_id = await self._get_my_id()

        return await self.instance.get_custom_reward(my_id)

    async def create_custom_redeem(self, data: Redeem):
        my_id = await self._get_my_id()

        await self.instance.create_custom_reward(my_id, title=data.title,
                                                 prompt=data.description,
                                                 cost=data.cost,
                                                 is_enabled=data.enabled)
