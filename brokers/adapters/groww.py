import requests
from django.conf import settings
from growwapi import GrowwAPI
from growwapi.groww import exceptions as groww_errors

from brokers.adapters.base import BrokerAdapter, LoginResult, OrderStatus, network_error, next_ist
from brokers.errors import BrokerError, ErrorCode, classify_message

REQUEST_TIMEOUT = 10
FINAL_STATES = {
    "EXECUTED": OrderStatus.COMPLETE,
    "DELIVERY_AWAITED": OrderStatus.COMPLETE,
    "COMPLETED": OrderStatus.COMPLETE,
    "REJECTED": OrderStatus.REJECTED,
    "FAILED": OrderStatus.REJECTED,
    "CANCELLED": OrderStatus.CANCELLED,
}


class QuietGrowwAPI(GrowwAPI):
    def _display_changelog(self):
        pass


class GrowwAdapter(BrokerAdapter):
    order_type = GrowwAPI.ORDER_TYPE_MARKET
    required_settings = ("GROWW_API_KEY", "GROWW_API_SECRET")

    def __init__(self, access_token="", user_id=None):
        super().__init__(access_token, user_id)
        self._groww = None

    def _check_config(self):
        if not settings.GROWW_API_KEY or not settings.GROWW_API_SECRET:
            raise BrokerError(ErrorCode.NOT_ALLOWED, "Groww is not configured on this server (GROWW_API_KEY / GROWW_API_SECRET missing)")

    @property
    def groww(self):
        self._check_config()
        if self._groww is None:
            self._groww = QuietGrowwAPI(self.access_token)
        return self._groww

    def _call(self, fn, *args, placing=False, **kwargs):
        try:
            return fn(*args, **kwargs)
        except groww_errors.GrowwAPIException as error:
            raise self._translate(error, placing)
        except requests.RequestException as error:
            raise network_error(error, "Groww", placing)

    def _translate(self, error, placing):
        message = error.msg
        if isinstance(error, groww_errors.GrowwAPIAuthenticationException):
            return BrokerError(ErrorCode.AUTH_EXPIRED, message)
        if isinstance(error, groww_errors.GrowwAPIAuthorisationException):
            return BrokerError(ErrorCode.NOT_ALLOWED, message)
        if isinstance(error, groww_errors.GrowwAPIRateLimitException):
            return BrokerError(ErrorCode.RATE_LIMITED, message)
        if isinstance(error, groww_errors.GrowwAPITimeoutException) or str(error.code).startswith("5"):
            return BrokerError(ErrorCode.TIMEOUT if placing else ErrorCode.BROKER_UNAVAILABLE, message)
        return BrokerError(classify_message(message), message)

    def get_login_url(self, state):
        return None

    def complete_login(self, params):
        self._check_config()
        try:
            token = self._call(GrowwAPI.get_access_token, api_key=settings.GROWW_API_KEY, secret=settings.GROWW_API_SECRET)
        except BrokerError as error:
            raise BrokerError(
                ErrorCode.AUTH_EXPIRED,
                f"Groww login failed: {error.message.rstrip('.')}. Approve today's API key on Groww Cloud (groww.in/trade-api/api-keys) and try again.",
            )
        return LoginResult(access_token=token, expires_at=next_ist(6))

    def get_holdings(self):
        response = self._call(self.groww.get_holdings_for_user, timeout=REQUEST_TIMEOUT)
        holdings = {}
        for item in response.get("holdings", []):
            sellable = int(item.get("demat_free_quantity") or 0) + int(item.get("t1_quantity") or 0)
            holdings[item["trading_symbol"]] = holdings.get(item["trading_symbol"], 0) + sellable
        return {symbol: quantity for symbol, quantity in holdings.items() if quantity > 0}

    def place_order(self, symbol, side, quantity, tag):
        response = self._call(
            self.groww.place_order,
            placing=True,
            validity=GrowwAPI.VALIDITY_DAY,
            exchange=GrowwAPI.EXCHANGE_NSE,
            order_type=self.order_type,
            product=GrowwAPI.PRODUCT_CNC,
            quantity=quantity,
            segment=GrowwAPI.SEGMENT_CASH,
            trading_symbol=symbol,
            transaction_type=side,
            order_reference_id=tag,
            timeout=REQUEST_TIMEOUT,
        )
        return response["groww_order_id"]

    def get_order_status(self, broker_order_id):
        response = self._call(
            self.groww.get_order_status,
            segment=GrowwAPI.SEGMENT_CASH,
            groww_order_id=broker_order_id,
            timeout=REQUEST_TIMEOUT,
        )
        state = FINAL_STATES.get(response.get("order_status"), OrderStatus.OPEN)
        message = response.get("remark") or ""
        return OrderStatus(
            state=state,
            filled_quantity=int(response.get("filled_quantity") or 0),
            message=message,
            error_code=classify_message(message) if state == OrderStatus.REJECTED else "",
        )

    def find_order_by_tag(self, tag):
        try:
            response = self.groww.get_order_status_by_reference(
                segment=GrowwAPI.SEGMENT_CASH,
                order_reference_id=tag,
                timeout=REQUEST_TIMEOUT,
            )
        except groww_errors.GrowwAPINotFoundException:
            return None
        except groww_errors.GrowwAPIException as error:
            raise self._translate(error, placing=False)
        except requests.RequestException as error:
            raise network_error(error, "Groww")
        return response.get("groww_order_id")
