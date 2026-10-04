import functools
import tempfile

import requests
from django.conf import settings
from fyers_apiv3 import fyersModel

from brokers.adapters.base import BrokerAdapter, LoginResult, OrderStatus, network_error, next_ist, no_reply, sellable_holdings
from brokers.errors import BrokerError, ErrorCode, classify_message

REQUEST_TIMEOUT = 10
SIDES = {"BUY": 1, "SELL": -1}
AUTH_CODES = {-8, -15, -16, -17}
NO_ACK_CODE = 201
FINAL_STATES = {2: OrderStatus.COMPLETE, 5: OrderStatus.REJECTED, 1: OrderStatus.CANCELLED, 7: OrderStatus.CANCELLED}


def to_fyers_symbol(symbol):
    return f"NSE:{symbol}-EQ"


def from_fyers_symbol(fyers_symbol):
    return fyers_symbol.split(":")[-1].rsplit("-", 1)[0]


class FyersAdapter(BrokerAdapter):
    order_type = 2
    required_settings = ("FYERS_APP_ID", "FYERS_SECRET_KEY", "FYERS_REDIRECT_URI")

    @functools.cached_property
    def fyers(self):
        self.check_config()
        model = fyersModel.FyersModel(
            client_id=settings.FYERS_APP_ID,
            token=self.access_token,
            is_async=False,
            log_path=tempfile.gettempdir(),
        )
        session = model.service.session
        session.request = functools.partial(session.request, timeout=REQUEST_TIMEOUT)
        return model

    def _call(self, fn, *args, placing=False):
        self.fyers.service.error_resp = {"s": "error", "code": -99, "message": ""}
        try:
            response = fn(*args)
        except requests.RequestException as error:
            raise network_error(error, "Fyers", placing)
        if not isinstance(response, dict):
            raise no_reply(f"Unexpected Fyers response: {response}", placing)
        if placing and response.get("code") == NO_ACK_CODE:
            raise BrokerError(ErrorCode.TIMEOUT, response.get("message") or "Fyers accepted the request but sent no acknowledgement")
        if response.get("s") == "ok":
            return response
        raise self._translate(response, placing)

    def _translate(self, response, placing):
        code = response.get("code")
        message = str(response.get("message") or "")
        if code in AUTH_CODES:
            return BrokerError(ErrorCode.AUTH_EXPIRED, message)
        if code == -429:
            return BrokerError(ErrorCode.RATE_LIMITED, message)
        if code == -300:
            return BrokerError(ErrorCode.INVALID_SYMBOL, message)
        classified = classify_message(message)
        if classified == ErrorCode.UNKNOWN and (code == -99 or (isinstance(code, int) and code >= 500)):
            return no_reply(message or f"No usable response from Fyers (code {code})", placing)
        return BrokerError(classified, message or f"Fyers error code {code}")

    def get_login_url(self, state):
        self.check_config()
        session = fyersModel.SessionModel(
            client_id=settings.FYERS_APP_ID,
            redirect_uri=settings.FYERS_REDIRECT_URI,
            response_type="code",
            state=state,
        )
        return session.generate_authcode()

    def complete_login(self, params):
        self.check_config()
        auth_code = params.get("auth_code")
        if not auth_code:
            raise BrokerError(ErrorCode.AUTH_EXPIRED, "Fyers login was cancelled or returned no auth_code")
        session = fyersModel.SessionModel(
            client_id=settings.FYERS_APP_ID,
            secret_key=settings.FYERS_SECRET_KEY,
            grant_type="authorization_code",
        )
        session.set_token(auth_code)
        try:
            response = session.generate_token()
        except requests.RequestException as error:
            raise network_error(error, "Fyers")
        if response.get("s") != "ok" or not response.get("access_token"):
            raise BrokerError(ErrorCode.AUTH_EXPIRED, f"Fyers login failed: {response.get('message', response)}")
        return LoginResult(access_token=response["access_token"], expires_at=next_ist(6))

    def get_holdings(self):
        return sellable_holdings(
            (from_fyers_symbol(item["symbol"]), int(item.get("remainingQuantity") or 0) + int(item.get("qty_t1") or 0))
            for item in self._call(self.fyers.holdings).get("holdings", [])
        )

    def place_order(self, symbol, side, quantity, tag):
        response = self._call(
            self.fyers.place_order,
            {
                "symbol": to_fyers_symbol(symbol),
                "qty": quantity,
                "type": self.order_type,
                "side": SIDES[side],
                "productType": "CNC",
                "limitPrice": 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": False,
                "orderTag": tag,
            },
            placing=True,
        )
        return str(response["id"])

    def get_order_status(self, broker_order_id):
        orders = self._call(self.fyers.orderbook, {"id": broker_order_id}).get("orderBook", [])
        if not orders:
            raise BrokerError(ErrorCode.BROKER_UNAVAILABLE, f"Fyers returned no order for id {broker_order_id}")
        return OrderStatus(
            state=FINAL_STATES.get(orders[0].get("status"), OrderStatus.OPEN),
            filled_quantity=int(orders[0].get("filledQty") or 0),
            message=orders[0].get("message") or "",
        )

    def find_order_by_tag(self, tag):
        for order in self._call(self.fyers.orderbook).get("orderBook", []):
            if order.get("orderTag") in (tag, f"1:{tag}"):
                return str(order["id"])
        return None
