from django.db import models


class ErrorCode(models.TextChoices):
    NOT_ENOUGH_SHARES = "NOT_ENOUGH_SHARES"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    INVALID_SYMBOL = "INVALID_SYMBOL"
    MARKET_CLOSED = "MARKET_CLOSED"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    NOT_ALLOWED = "NOT_ALLOWED"
    SELL_NOT_AUTHORIZED = "SELL_NOT_AUTHORIZED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    PRICE_OUT_OF_RANGE = "PRICE_OUT_OF_RANGE"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    BROKER_UNAVAILABLE = "BROKER_UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class BrokerError(Exception):
    def __init__(self, code, message=""):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
