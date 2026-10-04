from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.utils import timezone

from brokers.errors import BrokerError, ErrorCode, classify_message

IST = ZoneInfo("Asia/Kolkata")


def next_ist(hour, minute=0):
    now = timezone.now().astimezone(IST)
    expiry = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return expiry if expiry > now else expiry + timedelta(days=1)


def no_reply(message, placing):
    return BrokerError(ErrorCode.TIMEOUT if placing else ErrorCode.BROKER_UNAVAILABLE, message)


def network_error(error, broker, placing=False):
    if placing and not isinstance(error, requests.ConnectTimeout):
        return no_reply(f"{broker} did not respond: {error}", placing)
    return no_reply(f"{broker} unreachable: {error}", placing=False)


def sellable_holdings(rows):
    totals = Counter()
    for symbol, quantity in rows:
        totals[symbol] += quantity
    return {symbol: quantity for symbol, quantity in totals.items() if quantity > 0}


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

    def __post_init__(self):
        if self.state == self.REJECTED and not self.error_code:
            self.error_code = classify_message(self.message)


OMS_STATES = {
    "complete": OrderStatus.COMPLETE,
    "rejected": OrderStatus.REJECTED,
    "cancelled": OrderStatus.CANCELLED,
    "cancelled after market order": OrderStatus.CANCELLED,
}


class BrokerAdapter(ABC):
    order_type = "MARKET"
    required_settings = ()

    @classmethod
    def missing_settings(cls):
        return [name for name in cls.required_settings if not getattr(settings, name, "")]

    @classmethod
    def is_configured(cls):
        return not cls.missing_settings()

    def check_config(self):
        missing = self.missing_settings()
        if missing:
            name = type(self).__name__.removesuffix("Adapter")
            raise BrokerError(ErrorCode.NOT_ALLOWED, f"{name} is not configured on this server ({', '.join(missing)} missing)")

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
