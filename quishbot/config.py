import os

from twitchAPI.twitch import AuthScope


LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO").upper()

APP_ID = os.getenv('CLIENT_ID', "")
APP_SECRET = os.getenv('CLIENT_SECRET', "")
TARGET_SCOPES = [AuthScope.CHANNEL_READ_REDEMPTIONS,
                 AuthScope.CHANNEL_MANAGE_REDEMPTIONS]

WS_HOST = os.getenv("WS_HOST")
WS_PASS = os.getenv("WS_PASS")

SQUISH_REDEEM_ID="d30865cd-d04d-4d11-bc92-5bb333d5f9da"
SQUISH_FILTER_NAME = "SQUISH START"

CALLBACK_URL="http://localhost:5000/"

REDIS_PASSWORD=os.getenv("REDIS_PASSWORD")

TWITCH_ID=os.getenv("TWITCH_ID", "")
