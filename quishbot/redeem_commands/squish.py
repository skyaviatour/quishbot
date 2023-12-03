import asyncio

from quishbot import obs
from quishbot.config import SQUISH_FILTER_NAME

title = "squish me"
description = "i deserve it"
cost = 100
enabled = True
queue_name = "squish"


async def handle():
    conn = obs.get_connection()

    scenes = conn.get_scene_list()
    if not scenes:
        exit(2)

    current_scene_name = scenes.current_program_scene_name  # type: ignore

    # The redeem takes around 600ms + 800ms + 300ms to execute, but toggling the
    # filter returns instantly. So we delay the end of the function to not
    # overconsume messages
    conn.set_source_filter_enabled(current_scene_name, SQUISH_FILTER_NAME, True)
    await asyncio.sleep(2)
