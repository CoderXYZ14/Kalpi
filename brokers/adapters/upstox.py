import json
import threading
from functools import cached_property
from urllib.parse import urlencode

import upstox_client
import urllib3
from cachetools import TTLCache, cached
from django.conf import settings
from upstox_client.rest import ApiException

from brokers.adapters.base import OMS_STATES, BrokerAdapter, LoginResult, OrderStatus, next_ist, no_reply, sellable_holdings
from brokers.errors import BrokerError, ErrorCode, classify_message

API_VERSION = "2.0"
REQUEST_TIMEOUT = 10
LOGIN_DIALOG_URL = "https://api.upstox.com/v2/login/authorization/dialog"
ERROR_CODES = {
    "UDAPI1154": ErrorCode.NOT_ALLOWED,
    "UDAPI1158": ErrorCode.NOT_ALLOWED,
    "UDAPI100074": ErrorCode.MARKET_CLOSED,
}
ORDER_NOT_FOUND = "UDAPI100010"
NOT_SENT_ERRORS = (urllib3.exceptions.ConnectTimeoutError, urllib3.exceptions.NewConnectionError)


def _error_details(error):
    try:
        first = json.loads(error.body)["errors"][0]
        return first.get("errorCode") or first.get("error_code") or "", first.get("message") or str(error.reason)
    except (TypeError, ValueError, KeyError, IndexError):
        return "", str(error.reason or error)


class UpstoxAdapter(BrokerAdapter):
    market_protection = -1
    required_settings = ("UPSTOX_API_KEY", "UPSTOX_API_SECRET", "UPSTOX_REDIRECT_URI")

    def __init__(self, access_token="", user_id=None):
        super().__init__(access_token, user_id)
        self._holding_keys = {}

    @cached_property
    def client(self):
        self.check_config()
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        return upstox_client.ApiClient(configuration)

    def _call(self, fn, *args, placing=False, **kwargs):
        try:
            return fn(*args, _request_timeout=REQUEST_TIMEOUT, **kwargs)
        except ApiException as error:
            raise self._translate(error, placing)
        except urllib3.exceptions.HTTPError as error:
            reason = getattr(error, "reason", None) or error
            if placing and not isinstance(reason, NOT_SENT_ERRORS):
                raise BrokerError(ErrorCode.TIMEOUT, f"Upstox did not respond: {reason}")
            raise BrokerError(ErrorCode.BROKER_UNAVAILABLE, f"Upstox unreachable: {reason}")

    def _translate(self, error, placing):
        code, message = _error_details(error)
        if code in ERROR_CODES:
            return BrokerError(ERROR_CODES[code], message)
        if error.status == 401:
            return BrokerError(ErrorCode.AUTH_EXPIRED, message)
        if error.status == 429:
            return BrokerError(ErrorCode.RATE_LIMITED, message)
        if error.status == 0 or error.status >= 500:
            return no_reply(message, placing)
        return BrokerError(classify_message(message), message)

    def get_login_url(self, state):
        self.check_config()
        query = urlencode({
            "response_type": "code",
            "client_id": settings.UPSTOX_API_KEY,
            "redirect_uri": settings.UPSTOX_REDIRECT_URI,
            "state": state,
        })
        return f"{LOGIN_DIALOG_URL}?{query}"

    def complete_login(self, params):
        self.check_config()
        code = params.get("code")
        if not code:
            raise BrokerError(ErrorCode.AUTH_EXPIRED, "Upstox login was cancelled or returned no code")
        response = self._call(
            upstox_client.LoginApi(upstox_client.ApiClient()).token,
            API_VERSION,
            code=code,
            client_id=settings.UPSTOX_API_KEY,
            client_secret=settings.UPSTOX_API_SECRET,
            redirect_uri=settings.UPSTOX_REDIRECT_URI,
            grant_type="authorization_code",
        )
        return LoginResult(access_token=response.access_token, expires_at=next_ist(3, 30))

    def get_holdings(self):
        items = self._call(upstox_client.PortfolioApi(self.client).get_holdings, API_VERSION).data or []
        for item in items:
            if item.instrument_token and item.instrument_token.startswith("NSE_EQ|"):
                self._holding_keys[item.trading_symbol] = item.instrument_token
        return sellable_holdings(
            (item.trading_symbol, (item.quantity or 0) + (item.t1_quantity or 0) - (item.cnc_used_quantity or 0))
            for item in items
        )

    @cached(TTLCache(maxsize=10_000, ttl=12 * 60 * 60), key=lambda _, symbol: symbol, lock=threading.Lock())
    def instrument_key(self, symbol):
        response = self._call(upstox_client.InstrumentsApi(self.client).search_instrument, symbol, exchanges="NSE", segments="EQ")
        for item in response.data or []:
            if item.get("trading_symbol") == symbol and item.get("segment") == "NSE_EQ":
                return item["instrument_key"]
        raise BrokerError(ErrorCode.INVALID_SYMBOL, f"{symbol} not found on NSE (Upstox instrument search)")

    def place_order(self, symbol, side, quantity, tag):
        body = upstox_client.PlaceOrderV3Request(
            quantity=quantity,
            product="D",
            validity="DAY",
            price=0,
            tag=tag,
            instrument_token=self._holding_keys.get(symbol) or self.instrument_key(symbol),
            order_type=self.order_type,
            transaction_type=side,
            disclosed_quantity=0,
            trigger_price=0,
            is_amo=False,
            slice=False,
            market_protection=self.market_protection,
        )
        response = self._call(upstox_client.OrderApiV3(self.client).place_order, body, placing=True)
        return response.data.order_ids[0]

    def get_order_status(self, broker_order_id):
        order = self._call(upstox_client.OrderApi(self.client).get_order_details, api_version=API_VERSION, order_id=broker_order_id).data
        return OrderStatus(
            state=OMS_STATES.get((order.status or "").lower(), OrderStatus.OPEN),
            filled_quantity=order.filled_quantity or 0,
            message=order.status_message or "",
        )

    def find_order_by_tag(self, tag):
        try:
            order = upstox_client.OrderApi(self.client).get_order_details(
                api_version=API_VERSION, tag=tag, _request_timeout=REQUEST_TIMEOUT
            ).data
        except ApiException as error:
            if _error_details(error)[0] == ORDER_NOT_FOUND:
                return None
            raise self._translate(error, placing=False)
        except urllib3.exceptions.HTTPError as error:
            raise BrokerError(ErrorCode.BROKER_UNAVAILABLE, f"Upstox unreachable: {error}")
        return order.order_id if order else None
