from brokers.adapters.mock import MockAdapter
from brokers.adapters.zerodha import ZerodhaAdapter

ADAPTERS = {
    "mock": MockAdapter,
    "zerodha": ZerodhaAdapter,
}


def get_adapter(broker, access_token="", user_id=None):
    return ADAPTERS[broker](access_token=access_token, user_id=user_id)
