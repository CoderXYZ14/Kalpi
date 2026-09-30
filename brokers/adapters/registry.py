from brokers.adapters.groww import GrowwAdapter
from brokers.adapters.mock import MockAdapter
from brokers.adapters.upstox import UpstoxAdapter
from brokers.adapters.zerodha import ZerodhaAdapter

ADAPTERS = {
    "mock": MockAdapter,
    "zerodha": ZerodhaAdapter,
    "groww": GrowwAdapter,
    "upstox": UpstoxAdapter,
}


def get_adapter(broker, access_token="", user_id=None):
    return ADAPTERS[broker](access_token=access_token, user_id=user_id)
