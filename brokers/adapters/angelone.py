import threading
from datetime import datetime, timezone as dt_timezone
from functools import cache
from unittest.mock import patch
from urllib.parse import urlencode

import jwt
import requests
from cachetools import TTLCache, cached
from django.conf import settings

from brokers.adapters.base import BrokerAdapter, LoginResult, OrderStatus, network_error, next_ist
from brokers.errors import BrokerError, ErrorCode, classify_message

LOGIN_URL = "https://smartapi.angelone.in/publisher-login"
TAG_LENGTH = 19
FINAL_STATES = {
    "complete": OrderStatus.COMPLETE,
    "rejected": OrderStatus.REJECTED,
    "cancelled": OrderStatus.CANCELLED,
    "cancelled after market order": OrderStatus.CANCELLED,
}
ERROR_CODES = {
    "AG8001": ErrorCode.AUTH_EXPIRED,
    "AG8002": ErrorCode.AUTH_EXPIRED,
    "AG8003": ErrorCode.AUTH_EXPIRED,
    "AB1010": ErrorCode.AUTH_EXPIRED,
    "AB1011": ErrorCode.AUTH_EXPIRED,
    "AB1009": ErrorCode.INVALID_SYMBOL,
    "AB1006": ErrorCode.NOT_ALLOWED,
}
RETRYABLE_CODES = {"AB1004", "AB2001"}


@cache
def smart_connect_class():
    import logzero

    logzero.logger.disabled = True
    with patch("requests.get", side_effect=OSError("public IP lookup disabled")):
        from SmartApi.smartConnect import SmartConnect
    return SmartConnect


def token_expiry(access_token):
    try:
        claims = jwt.decode(access_token, options={"verify_signature": False})
        return datetime.fromtimestamp(claims["exp"], tz=dt_timezone.utc)
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return next_ist(6)


class AngelOneAdapter(BrokerAdapter):
    order_type = "MARKET"

    def __init__(self, access_token="", user_id=None):
        super().__init__(access_token, user_id)
        self._client = None
        self._holding_tokens = {}

    def _check_config(self):
        if not settings.ANGEL_API_KEY:
            raise BrokerError(ErrorCode.NOT_ALLOWED, "AngelOne is not configured on this server (ANGEL_API_KEY missing)")

    @property
    def client(self):
        self._check_config()
        if self._client is None:
            client_class = smart_connect_class()
            with patch("logzero.logfile"):
                self._client = client_class(api_key=settings.ANGEL_API_KEY, access_token=self.access_token)
            if settings.ANGEL_CLIENT_PUBLIC_IP:
                self._client.clientPublicIp = settings.ANGEL_CLIENT_PUBLIC_IP
        return self._client

    def _call(self, fn, *args, placing=False):
        try:
            response = fn(*args)
        except requests.RequestException as error:
            raise network_error(error, "AngelOne", placing)
        except Exception as error:
            raise self._translate_exception(error, placing)
        if not isinstance(response, dict):
            raise BrokerError(ErrorCode.TIMEOUT if placing else ErrorCode.BROKER_UNAVAILABLE, f"Unexpected AngelOne response: {response}")
        if response.get("status") is True:
            return response
        raise self._translate(response.get("errorcode") or "", str(response.get("message") or ""), placing)

    def _translate_exception(self, error, placing):
        from SmartApi import smartExceptions

        if not isinstance(error, smartExceptions.SmartAPIException):
            raise error
        if isinstance(error, smartExceptions.TokenException):
            return BrokerError(ErrorCode.AUTH_EXPIRED, str(error))
        if isinstance(error, (smartExceptions.NetworkException, smartExceptions.DataException)) or error.code >= 500:
            return BrokerError(ErrorCode.TIMEOUT if placing else ErrorCode.BROKER_UNAVAILABLE, str(error))
        return BrokerError(classify_message(str(error)), str(error))

    def _translate(self, code, message, placing):
        if code in ERROR_CODES:
            return BrokerError(ERROR_CODES[code], message)
        if code in RETRYABLE_CODES:
            return BrokerError(ErrorCode.TIMEOUT if placing else ErrorCode.BROKER_UNAVAILABLE, message)
        return BrokerError(classify_message(message), message or f"AngelOne error {code}")

    def get_login_url(self, state):
        self._check_config()
        return f"{LOGIN_URL}?{urlencode({'api_key': settings.ANGEL_API_KEY, 'state': state})}"

    def complete_login(self, params):
        self._check_config()
        auth_token = params.get("auth_token")
        if not auth_token:
            raise BrokerError(ErrorCode.AUTH_EXPIRED, "AngelOne login was cancelled or returned no auth_token")
        return LoginResult(access_token=auth_token, expires_at=token_expiry(auth_token))

    def get_holdings(self):
        holdings = {}
        for item in self._call(self.client.holding).get("data") or []:
            symbol = item["tradingsymbol"].rsplit("-", 1)[0]
            sellable = int(item.get("quantity") or 0) + int(item.get("t1quantity") or 0)
            holdings[symbol] = holdings.get(symbol, 0) + sellable
            if item.get("exchange") == "NSE" and item.get("symboltoken"):
                self._holding_tokens[symbol] = str(item["symboltoken"])
        return {symbol: quantity for symbol, quantity in holdings.items() if quantity > 0}

    @cached(TTLCache(maxsize=10_000, ttl=12 * 60 * 60), key=lambda self, symbol: symbol, lock=threading.Lock())
    def symbol_token(self, symbol):
        for item in self._call(self.client.searchScrip, "NSE", symbol).get("data") or []:
            if item.get("tradingsymbol") == f"{symbol}-EQ":
                return str(item["symboltoken"])
        raise BrokerError(ErrorCode.INVALID_SYMBOL, f"{symbol} not found on NSE (AngelOne scrip search)")

    def place_order(self, symbol, side, quantity, tag):
        response = self._call(
            self.client.placeOrderFullResponse,
            {
                "variety": "NORMAL",
                "tradingsymbol": f"{symbol}-EQ",
                "symboltoken": self._holding_tokens.get(symbol) or self.symbol_token(symbol),
                "transactiontype": side,
                "exchange": "NSE",
                "ordertype": self.order_type,
                "producttype": "DELIVERY",
                "duration": "DAY",
                "price": "0",
                "quantity": str(quantity),
                "ordertag": tag[:TAG_LENGTH],
            },
            placing=True,
        )
        return str(response["data"]["orderid"])

    def _order_book(self):
        return self._call(self.client.orderBook).get("data") or []

    def get_order_status(self, broker_order_id):
        order = next((item for item in self._order_book() if str(item.get("orderid")) == broker_order_id), None)
        if order is None:
            raise BrokerError(ErrorCode.BROKER_UNAVAILABLE, f"AngelOne order book has no order {broker_order_id} yet")
        state = FINAL_STATES.get((order.get("status") or "").lower(), OrderStatus.OPEN)
        message = order.get("text") or ""
        return OrderStatus(
            state=state,
            filled_quantity=int(order.get("filledshares") or 0),
            message=message,
            error_code=classify_message(message) if state == OrderStatus.REJECTED else "",
        )

    def find_order_by_tag(self, tag):
        for order in self._order_book():
            if order.get("ordertag") == tag[:TAG_LENGTH]:
                return str(order["orderid"])
        return None
