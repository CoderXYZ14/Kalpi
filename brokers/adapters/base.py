from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.utils import timezone

from brokers.errors import BrokerError, ErrorCode

IST = ZoneInfo("Asia/Kolkata")


def next_ist(hour, minute=0):
    now = timezone.now().astimezone(IST)
    expiry = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return expiry if expiry > now else expiry + timedelta(days=1)


def network_error(error, broker, placing=False):
    if placing and not isinstance(error, requests.ConnectTimeout):
        return BrokerError(ErrorCode.TIMEOUT, f"{broker} did not respond: {error}")
    return BrokerError(ErrorCode.BROKER_UNAVAILABLE, f"{broker} unreachable: {error}")


@dataclass
class LoginResult:
    access_token: str
    expires_at: datetime


@dataclass
class OrderStatus:
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    OPEN = "OPEN"

    state: str
    filled_quantity: int
    message: str = ""
    error_code: str = ""


class BrokerAdapter(ABC):
    order_type = "MARKET"
    required_settings = ()

    @classmethod
    def is_configured(cls):
        return all(getattr(settings, name, "") for name in cls.required_settings)

    def __init__(self, access_token="", user_id=None):
        self.access_token = access_token
        self.user_id = user_id

    @abstractmethod
    def get_login_url(self, state):
        ...

    @abstractmethod
    def complete_login(self, params) -> LoginResult:
        ...

    @abstractmethod
    def get_holdings(self) -> dict[str, int]:
        ...

    @abstractmethod
    def place_order(self, symbol, side, quantity, tag) -> str:
        ...

    @abstractmethod
    def get_order_status(self, broker_order_id) -> OrderStatus:
        ...

    @abstractmethod
    def find_order_by_tag(self, tag) -> str | None:
        ...
