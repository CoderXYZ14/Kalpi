from urllib.parse import quote, urlencode

import requests
from django.conf import settings
from kiteconnect import KiteConnect
from kiteconnect import exceptions as kite_errors

from brokers.adapters.base import BrokerAdapter, LoginResult, OrderStatus, network_error, next_ist
from brokers.errors import BrokerError, ErrorCode, classify_message

FINAL_STATES = {"COMPLETE": OrderStatus.COMPLETE, "REJECTED": OrderStatus.REJECTED, "CANCELLED": OrderStatus.CANCELLED}


class ZerodhaAdapter(BrokerAdapter):
    order_type = KiteConnect.ORDER_TYPE_MARKET
    market_protection = -1
    required_settings = ("KITE_API_KEY", "KITE_API_SECRET")

    def __init__(self, access_token="", user_id=None):
        super().__init__(access_token, user_id)
        self._kite = None

    @property
    def kite(self):
        if not settings.KITE_API_KEY or not settings.KITE_API_SECRET:
            raise BrokerError(ErrorCode.NOT_ALLOWED, "Zerodha is not configured on this server (KITE_API_KEY / KITE_API_SECRET missing)")
        if self._kite is None:
            self._kite = KiteConnect(api_key=settings.KITE_API_KEY, access_token=self.access_token or None)
        return self._kite

    def _call(self, fn, *args, placing=False, **kwargs):
        try:
            return fn(*args, **kwargs)
        except kite_errors.KiteException as error:
            raise self._translate(error, placing)
        except requests.RequestException as error:
            raise network_error(error, "Zerodha", placing)

    def _translate(self, error, placing):
        message = str(error)
        if isinstance(error, kite_errors.TokenException):
            return BrokerError(ErrorCode.AUTH_EXPIRED, message)
        if isinstance(error, kite_errors.PermissionException):
            return BrokerError(ErrorCode.NOT_ALLOWED, message)
        if error.code == 403:
            return BrokerError(ErrorCode.AUTH_EXPIRED, message)
        if error.code == 429:
            return BrokerError(ErrorCode.RATE_LIMITED, message)
        if error.code == 428:
            return BrokerError(ErrorCode.SELL_NOT_AUTHORIZED, f"{message} Authorise holdings on Kite (CDSL TPIN) or enable DDPI.")
        if isinstance(error, (kite_errors.NetworkException, kite_errors.DataException)) or error.code >= 500:
            return BrokerError(ErrorCode.TIMEOUT if placing else ErrorCode.BROKER_UNAVAILABLE, message)
        return BrokerError(classify_message(message), message)

    def get_login_url(self, state):
        return f"{self.kite.login_url()}&redirect_params={quote(urlencode({'state': state}))}"

    def complete_login(self, params):
        request_token = params.get("request_token")
        if not request_token:
            raise BrokerError(ErrorCode.AUTH_EXPIRED, "Zerodha login was cancelled or returned no request_token")
        session = self._call(self.kite.generate_session, request_token, api_secret=settings.KITE_API_SECRET)
        return LoginResult(access_token=session["access_token"], expires_at=next_ist(6))

    def get_holdings(self):
        holdings = {}
        for item in self._call(self.kite.holdings):
            sellable = item.get("quantity", 0) + item.get("t1_quantity", 0) - item.get("used_quantity", 0)
            holdings[item["tradingsymbol"]] = holdings.get(item["tradingsymbol"], 0) + sellable
        return {symbol: quantity for symbol, quantity in holdings.items() if quantity > 0}

    def place_order(self, symbol, side, quantity, tag):
        order_id = self._call(
            self.kite.place_order,
            placing=True,
            variety=KiteConnect.VARIETY_REGULAR,
            exchange=KiteConnect.EXCHANGE_NSE,
            tradingsymbol=symbol,
            transaction_type=side,
            quantity=quantity,
            product=KiteConnect.PRODUCT_CNC,
            order_type=self.order_type,
            validity=KiteConnect.VALIDITY_DAY,
            market_protection=self.market_protection if self.order_type == KiteConnect.ORDER_TYPE_MARKET else None,
            tag=tag,
        )
        return str(order_id)

    def get_order_status(self, broker_order_id):
        latest = self._call(self.kite.order_history, broker_order_id)[-1]
        state = FINAL_STATES.get(latest["status"], OrderStatus.OPEN)
        message = latest.get("status_message") or ""
        return OrderStatus(
            state=state,
            filled_quantity=latest.get("filled_quantity") or 0,
            message=message,
            error_code=classify_message(message) if state == OrderStatus.REJECTED else "",
        )

    def find_order_by_tag(self, tag):
        for order in self._call(self.kite.orders):
            if order.get("tag") == tag or tag in (order.get("tags") or []):
                return str(order["order_id"])
        return None
