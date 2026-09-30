import logging
import threading
import time
from datetime import time as clock_time
from functools import cache
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import connection
from django.utils import timezone
from pyrate_limiter import Duration, Limiter, Rate
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

from brokers.adapters.base import OrderStatus
from brokers.adapters.registry import get_adapter
from brokers.errors import BrokerError, ErrorCode
from executions.models import Execution, Order
from notifications.notifier import notify

logger = logging.getLogger("engine")

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = clock_time(9, 15)
MARKET_CLOSE = clock_time(15, 30)
TRANSIENT_ERRORS = {ErrorCode.RATE_LIMITED, ErrorCode.BROKER_UNAVAILABLE}


class StopExecution(Exception):
    def __init__(self, code, message):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def normalize(payload):
    orders = []
    for item in payload.get("sell", []):
        orders.append((item["symbol"], Order.Side.SELL, item["quantity"]))
    for item in payload.get("buy", []):
        orders.append((item["symbol"], Order.Side.BUY, item["quantity"]))
    for item in payload.get("rebalance", []):
        change = item["quantity_change"]
        if change < 0:
            orders.append((item["symbol"], Order.Side.SELL, -change))
        elif change > 0:
            orders.append((item["symbol"], Order.Side.BUY, change))
    return sorted(orders, key=lambda order: order[1] != Order.Side.SELL)


def is_market_open(now=None):
    now = (now or timezone.now()).astimezone(IST)
    return now.weekday() < 5 and MARKET_OPEN <= now.time() <= MARKET_CLOSE


def is_transient(error):
    return isinstance(error, BrokerError) and error.code in TRANSIENT_ERRORS


@cache
def order_limiter(broker):
    return Limiter(Rate(settings.ENGINE_ORDERS_PER_SECOND, Duration.SECOND))


class ExecutionRunner:
    def __init__(self, execution):
        self.execution = execution
        self.account = execution.broker_account
        self.adapter = get_adapter(self.account.broker, self.account.access_token, self.account.user_id)

    def log(self, message, *args, level=logging.INFO):
        logger.log(level, f"[exec {str(self.execution.id)[:8]}] {message}", *args)

    def run(self):
        self.log("started: mode=%s broker=%s", self.execution.mode, self.account.broker)
        if not self.account.is_connected():
            raise StopExecution(ErrorCode.AUTH_EXPIRED, f"{self.account.broker} session expired or not connected. Login again.")
        if not settings.BYPASS_MARKET_HOURS and not is_market_open():
            raise StopExecution(ErrorCode.MARKET_CLOSED, "Market is open 09:15-15:30 IST, Monday to Friday")

        orders = list(self.execution.orders.all())
        sells = [order for order in orders if order.side == Order.Side.SELL]
        buys = [order for order in orders if order.side == Order.Side.BUY]

        if sells:
            self.check_holdings(sells)
            self.run_phase("SELL", [order for order in sells if order.status == Order.Status.QUEUED])
        self.run_phase("BUY", buys)

    def check_holdings(self, sells):
        try:
            holdings = self.call_with_retry(self.adapter.get_holdings)
        except BrokerError as error:
            raise StopExecution(error.code, f"Could not fetch holdings: {error.message}")
        self.log("holdings: %s", holdings)
        for order in sells:
            held = holdings.get(order.symbol, 0)
            if order.quantity > held:
                self.fail(order, ErrorCode.NOT_ENOUGH_SHARES, f"Trying to sell {order.quantity}, only {held} held")

    def run_phase(self, name, orders):
        if not orders:
            return
        self.log("%s phase: %d orders", name, len(orders))
        placed = [order for order in orders if self.place(order)]
        self.track(placed)

    def call_with_retry(self, fn, *args):
        retrying = Retrying(
            retry=retry_if_exception(is_transient),
            stop=stop_after_attempt(settings.ENGINE_RETRY_ATTEMPTS),
            wait=wait_exponential(multiplier=settings.ENGINE_RETRY_WAIT),
            before_sleep=self.log_retry,
            reraise=True,
        )
        try:
            return retrying(fn, *args)
        except BrokerError as error:
            if error.code == ErrorCode.AUTH_EXPIRED:
                raise StopExecution(error.code, error.message)
            raise

    def log_retry(self, retry_state):
        error = retry_state.outcome.exception()
        self.log("%s, retry %d in %.1fs", error.code, retry_state.attempt_number, retry_state.next_action.sleep, level=logging.WARNING)

    def send_order(self, order):
        order_limiter(self.account.broker).try_acquire(self.account.broker)
        return self.adapter.place_order(order.symbol, order.side, order.quantity, order.tag)

    def place(self, order):
        try:
            try:
                order.broker_order_id = self.call_with_retry(self.send_order, order)
            except BrokerError as error:
                if error.code != ErrorCode.TIMEOUT:
                    raise
                order.broker_order_id = self.recover_after_timeout(order)
        except BrokerError as error:
            self.fail(order, error.code, error.message)
            return False

        order.status = Order.Status.PLACED
        order.save()
        self.log("placed %s %s x%d tag=%s -> %s", order.side, order.symbol, order.quantity, order.tag, order.broker_order_id)
        return True

    def recover_after_timeout(self, order):
        self.log("timeout on %s, checking broker for tag %s", order.symbol, order.tag, level=logging.WARNING)
        existing_id = self.lookup_tag(order)
        if existing_id:
            return existing_id

        self.log("tag %s not found at broker, retrying once", order.tag)
        try:
            return self.call_with_retry(self.send_order, order)
        except BrokerError as error:
            if error.code != ErrorCode.TIMEOUT:
                raise

        existing_id = self.lookup_tag(order)
        if existing_id:
            return existing_id
        raise BrokerError(ErrorCode.TIMEOUT, f"Timed out twice and order not found at broker. Check order book for tag {order.tag}.")

    def lookup_tag(self, order):
        try:
            existing_id = self.call_with_retry(self.adapter.find_order_by_tag, order.tag)
        except StopExecution:
            self.fail(order, ErrorCode.TIMEOUT, f"Timed out and session expired before confirming. Check order book for tag {order.tag}.")
            raise
        except BrokerError as error:
            raise BrokerError(
                ErrorCode.TIMEOUT,
                f"Timed out and could not confirm with broker ({error.message}). Check order book for tag {order.tag}.",
            )
        if existing_id:
            self.log("order with tag %s already exists at broker: %s", order.tag, existing_id)
        return existing_id

    def track(self, orders):
        deadline = time.monotonic() + settings.ENGINE_POLL_TIMEOUT
        open_orders = list(orders)
        while open_orders:
            open_orders = [order for order in open_orders if not self.update_status(order)]
            if not open_orders or time.monotonic() >= deadline:
                break
            time.sleep(settings.ENGINE_POLL_INTERVAL)

        for order in open_orders:
            order.status = Order.Status.PARTIAL if order.filled_quantity else Order.Status.PENDING
            order.error_message = (
                f"Still open at broker after {settings.ENGINE_POLL_TIMEOUT:g}s (e.g. upper/lower circuit). "
                "Order left open, check broker order book."
            )
            order.save()
            self.log("%s %s left open: %s", order.side, order.symbol, order.status, level=logging.WARNING)

    def update_status(self, order):
        try:
            status = self.adapter.get_order_status(order.broker_order_id)
        except BrokerError as error:
            if error.code == ErrorCode.AUTH_EXPIRED:
                raise StopExecution(error.code, error.message)
            self.log("status check failed for %s: %s", order.symbol, error, level=logging.WARNING)
            return False

        order.filled_quantity = min(status.filled_quantity, order.quantity)
        if order.filled_quantity == order.quantity:
            order.status = Order.Status.SUCCESS
        elif status.state in (OrderStatus.REJECTED, OrderStatus.CANCELLED):
            order.status = Order.Status.PARTIAL if order.filled_quantity else Order.Status.FAILED
            order.error_code = status.error_code or ("" if order.filled_quantity else ErrorCode.UNKNOWN)
            order.error_message = status.message
        else:
            order.save()
            return False

        order.save()
        self.log("%s %s -> %s (filled %d/%d)", order.side, order.symbol, order.status, order.filled_quantity, order.quantity)
        return True

    def fail(self, order, code, message):
        order.status = Order.Status.FAILED
        order.error_code = code
        order.error_message = message
        order.save()
        self.log("%s %s failed: %s %s", order.side, order.symbol, code, message, level=logging.WARNING)


def _close_open_orders(execution, reason):
    execution.orders.filter(status=Order.Status.QUEUED).update(status=Order.Status.SKIPPED, error_message=f"Not sent: {reason}")
    execution.orders.filter(status=Order.Status.PLACED).update(
        error_message=f"Sent to broker, final status unknown ({reason}). Check broker order book."
    )


def run_execution(execution_id):
    execution = Execution.objects.select_related("broker_account").get(id=execution_id)
    try:
        ExecutionRunner(execution).run()
        execution.status = Execution.Status.COMPLETED
    except StopExecution as stop:
        logger.warning("[exec %s] stopped: %s", str(execution.id)[:8], stop)
        _close_open_orders(execution, f"execution stopped, {stop.code}")
        execution.status = Execution.Status.STOPPED
        execution.error_message = f"{stop.code}: {stop.message}"
    except Exception as error:
        logger.exception("[exec %s] crashed", str(execution.id)[:8])
        _close_open_orders(execution, "internal error")
        execution.status = Execution.Status.STOPPED
        execution.error_message = f"Internal error: {error}"

    execution.finished_at = timezone.now()
    execution.save(update_fields=["status", "error_message", "finished_at"])
    logger.info("[exec %s] finished: %s", str(execution.id)[:8], execution.status)
    notify(execution)


def _run_in_thread(execution_id):
    try:
        run_execution(execution_id)
    finally:
        connection.close()


def start_execution(execution_id):
    threading.Thread(target=_run_in_thread, args=(execution_id,), name=f"exec-{execution_id}", daemon=True).start()


def recover_interrupted_executions():
    stuck = list(Execution.objects.select_related("broker_account").filter(status=Execution.Status.RUNNING))
    for execution in stuck:
        _close_open_orders(execution, "server restarted")
        execution.status = Execution.Status.STOPPED
        execution.error_message = "Interrupted by server restart. Check broker order book for PLACED orders."
        execution.finished_at = timezone.now()
        execution.save(update_fields=["status", "error_message", "finished_at"])
        logger.warning("[exec %s] marked STOPPED after restart", str(execution.id)[:8])
        notify(execution)
    return len(stuck)
