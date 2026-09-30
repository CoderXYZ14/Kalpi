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


MESSAGE_PATTERNS = [
    (("authorisation at depository", "needs authorisation", "tpin", "edis", "ddpi"), ErrorCode.SELL_NOT_AUTHORIZED),
    (("session", "token", "login"), ErrorCode.AUTH_EXPIRED),
    (("insufficient fund", "margin", "insufficient balance"), ErrorCode.INSUFFICIENT_FUNDS),
    (("holding", "insufficient quantity"), ErrorCode.NOT_ENOUGH_SHARES),
    (("circuit", "price range", "lpp", "price band"), ErrorCode.PRICE_OUT_OF_RANGE),
    (("market is closed", "markets are closed", "market closed", "outside market hours"), ErrorCode.MARKET_CLOSED),
    (("quantity", "lot size"), ErrorCode.INVALID_QUANTITY),
    (("instrument", "symbol", "scrip"), ErrorCode.INVALID_SYMBOL),
    (("not allowed", "blocked", "banned", "restricted", "suspended"), ErrorCode.NOT_ALLOWED),
    (("too many requests", "rate limit"), ErrorCode.RATE_LIMITED),
]


def classify_message(message):
    text = (message or "").lower()
    for keywords, code in MESSAGE_PATTERNS:
        if any(keyword in text for keyword in keywords):
            return code
    return ErrorCode.UNKNOWN


class BrokerError(Exception):
    def __init__(self, code, message=""):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
