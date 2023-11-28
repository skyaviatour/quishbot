import config

import obsws_python as obs


def get_connection():
    conn = obs.ReqClient(host=config.WS_HOST, password=config.WS_PASS)

    return conn
