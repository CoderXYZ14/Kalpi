import itertools
from datetime import timedelta

from django.utils import timezone

from brokers.adapters.base import BrokerAdapter, LoginResult, OrderStatus
from brokers.errors import BrokerError, ErrorCode

PRICE = 100
STARTING_CASH = 1_000_000
STARTING_HOLDINGS = {"INFY": 50, "TCS": 20, "HDFCBANK": 30, "TESTNOSELL": 10, "TESTCIRCUIT": 10, "TESTPARTIAL": 10}

_accounts = {}
_order_ids = itertools.count(1)


def _account(user_id):
    if user_id not in _accounts:
        _accounts[user_id] = {
            "cash": STARTING_CASH,
            "holdings": dict(STARTING_HOLDINGS),
            "orders": {},
            "rate_limited_tags": set(),
        }
    return _accounts[user_id]


class MockAdapter(BrokerAdapter):
    def __init__(self, access_token="", user_id=None):
        super().__init__(access_token, user_id)
        self.account = _account(user_id)

    def get_login_url(self, state):
        return None

    def complete_login(self, params):
        return LoginResult(access_token=f"mock-token-{self.user_id}", expires_at=timezone.now() + timedelta(days=1))

    def get_holdings(self):
        return {symbol: qty for symbol, qty in self.account["holdings"].items() if qty > 0}

    def place_order(self, symbol, side, quantity, tag):
        account = self.account

        if symbol == "TESTRATELIMIT" and tag not in account["rate_limited_tags"]:
            account["rate_limited_tags"].add(tag)
            raise BrokerError(ErrorCode.RATE_LIMITED, "Too many requests")
        if symbol == "TESTAUTHEXPIRE":
            raise BrokerError(ErrorCode.AUTH_EXPIRED, "Session expired, please login again")
        if symbol == "TESTNOTALLOWED":
            raise BrokerError(ErrorCode.NOT_ALLOWED, "Trading in this instrument is not allowed")
        if symbol == "TESTNOSELL" and side == "SELL":
            raise BrokerError(ErrorCode.SELL_NOT_AUTHORIZED, "Holdings not authorised for sell (eDIS/TPIN pending)")
        if side == "SELL" and quantity > account["holdings"].get(symbol, 0):
            raise BrokerError(ErrorCode.NOT_ENOUGH_SHARES, f"Only {account['holdings'].get(symbol, 0)} shares held")
        if side == "BUY" and quantity * PRICE > account["cash"]:
            raise BrokerError(ErrorCode.INSUFFICIENT_FUNDS, f"Required {quantity * PRICE}, available {account['cash']}")

        if symbol == "TESTCIRCUIT":
            state, filled = OrderStatus.OPEN, 0
        elif symbol == "TESTPARTIAL":
            state, filled = OrderStatus.CANCELLED, quantity // 2
        else:
            state, filled = OrderStatus.COMPLETE, quantity

        order_id = f"MOCK{next(_order_ids)}"
        message = "Remaining quantity cancelled" if state == OrderStatus.CANCELLED else ""
        account["orders"][order_id] = {"tag": tag, "status": OrderStatus(state, filled, message)}

        signed = filled if side == "BUY" else -filled
        account["holdings"][symbol] = account["holdings"].get(symbol, 0) + signed
        account["cash"] -= signed * PRICE

        if symbol == "TESTTIMEOUT":
            raise BrokerError(ErrorCode.TIMEOUT, "Request timed out")
        return order_id

    def get_order_status(self, broker_order_id):
        order = self.account["orders"].get(broker_order_id)
        if order is None:
            raise BrokerError(ErrorCode.UNKNOWN, f"Order {broker_order_id} not found")
        return order["status"]

    def find_order_by_tag(self, tag):
        for order_id, order in self.account["orders"].items():
            if order["tag"] == tag:
                return order_id
        return None
