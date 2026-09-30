from brokers.adapters.mock import MockAdapter

ADAPTERS = {
    "mock": MockAdapter,
}


def get_adapter(broker, access_token="", user_id=None):
    return ADAPTERS[broker](access_token=access_token, user_id=user_id)
