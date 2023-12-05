import logging
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.helper import first
from twitchAPI.object.eventsub import ChannelPointsCustomRewardRedemptionAddEvent
from twitchAPI.twitch import CustomReward, Twitch
from twitchAPI.type import CustomRewardRedemptionStatus
from quishbot.queues.generic import GenericQueue

from quishbot.types.redeem import Redeem


logger = logging.getLogger(__name__)


class TwitchHandler:
    instance: Twitch
    queue: GenericQueue
    event_sub_ws: EventSubWebsocket

    my_id: str | None

    redeems_map: dict[str, str]

    def __init__(self, instance: Twitch, queue: GenericQueue) -> None:
        self.instance = instance
        self.queue = queue

        self.my_id = None
        self.redeems_map = {}

    async def start(self):
        my_id = await self._get_my_id()

        self.event_sub_ws = EventSubWebsocket(self.instance)
        self.event_sub_ws.start()

        await self.event_sub_ws.listen_channel_points_custom_reward_redemption_add(
            my_id,
            self.handle_redeem_queue
        )

        logger.info("ready to accept redeems")

    async def stop(self):
        ...

    async def _get_my_id(self):
        if self.my_id is not None:
            return self.my_id

        me = await first(self.instance.get_users())

        if not me:
            exit(255)

        self.my_id = me.id

        return self.my_id

    async def handle_redeem_queue(self, data: ChannelPointsCustomRewardRedemptionAddEvent):
        redeem_title = data.event.reward.title

        if redeem_title in self.redeems_map:
            await self.queue.put_message(
                f"redeems:{self.redeems_map[redeem_title]}", f"{data.event.id}"
            )

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

    async def create_custom_redeem(self, data: Redeem) -> CustomReward:
        my_id = await self._get_my_id()

        return await self.instance.create_custom_reward(my_id, title=data.title,
                                                 prompt=data.description,
                                                 cost=data.cost,
                                                 is_enabled=data.enabled)

    async def refund_pending_redeems(self, redeem_id: str):
        my_id = await self._get_my_id()

        logger.debug(f"checking refunds for {redeem_id}")

        pending_redeems = self.instance.get_custom_reward_redemption(
            my_id,
            redeem_id,
            status=CustomRewardRedemptionStatus.UNFULFILLED
        )

        pending_redeems_ids: list[str] = [p.id async for p in pending_redeems]

        await self.instance.update_redemption_status(
            my_id,
            redeem_id,
            pending_redeems_ids,
            CustomRewardRedemptionStatus.CANCELED
        )

    async def confirm_custom_redeem(self, redeem_id: str, redeem_reward_id: str):
        my_id = await self._get_my_id()

        logger.debug(f"confirming redeem {redeem_id} {redeem_reward_id}")
        await self.instance.update_redemption_status(
            my_id,
            redeem_id,
            [redeem_reward_id],
            CustomRewardRedemptionStatus.FULFILLED
        )

    def register_redeem_queue(self, redeem_title: str, queue_name: str):
        self.redeems_map[redeem_title] = queue_name
