from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


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


class BrokerAdapter(ABC):
    order_type = "MARKET"

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
