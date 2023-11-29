import obsws_python as obs

from quishbot.config import WS_HOST, WS_PASS


def get_connection():
    conn = obs.ReqClient(host=WS_HOST, password=WS_PASS)

    return conn
