import json
import logging
from abc import ABC, abstractmethod

import requests
from django.conf import settings

logger = logging.getLogger("notifications")


class Notifier(ABC):
    @abstractmethod
    def send(self, summary):
        ...


class ConsoleNotifier(Notifier):
    def send(self, summary):
        logger.info("Execution summary:\n%s", json.dumps(summary, indent=2))


class WebhookNotifier(Notifier):
    def __init__(self, url):
        self.url = url

    def send(self, summary):
        response = requests.post(self.url, json=summary, timeout=5)
        response.raise_for_status()
        logger.info("[webhook] sent execution %s to %s", summary["execution_id"], self.url)


def build_summary(execution):
    orders = list(execution.orders.all())
    return {
        "execution_id": str(execution.id),
        "mode": execution.mode,
        "broker": execution.broker_account.broker,
        "status": execution.status,
        "error": execution.error_message,
        "created_at": execution.created_at.isoformat(),
        "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
        "counts": execution.status_counts(),
        "orders": [
            {
                "symbol": order.symbol,
                "side": order.side,
                "quantity": order.quantity,
                "filled_quantity": order.filled_quantity,
                "status": order.status,
                "error_code": order.error_code,
                "error_message": order.error_message,
            }
            for order in orders
        ],
    }


def get_notifiers():
    notifiers = [ConsoleNotifier()]
    if settings.WEBHOOK_URL:
        notifiers.append(WebhookNotifier(settings.WEBHOOK_URL))
    return notifiers


def notify(execution):
    try:
        summary = build_summary(execution)
    except Exception:
        logger.exception("[notify] could not build summary for execution %s", execution.id)
        return
    for notifier in get_notifiers():
        try:
            notifier.send(summary)
        except requests.RequestException as error:
            logger.warning("[notify] %s failed for execution %s: %s", notifier.__class__.__name__, execution.id, error)
        except Exception:
            logger.exception("[notify] %s failed for execution %s", notifier.__class__.__name__, execution.id)
