import uuid

from django.conf import settings
from django.db import models

from brokers.errors import ErrorCode


def new_order_tag():
    return uuid.uuid4().hex[:20]


class Execution(models.Model):
    class Mode(models.TextChoices):
        FIRST_TIME = "FIRST_TIME"
        REBALANCE = "REBALANCE"

    class Status(models.TextChoices):
        RUNNING = "RUNNING"
        COMPLETED = "COMPLETED"
        STOPPED = "STOPPED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="executions")
    broker_account = models.ForeignKey("brokers.BrokerAccount", on_delete=models.PROTECT, related_name="executions")
    mode = models.CharField(max_length=20, choices=Mode.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    idempotency_key = models.CharField(max_length=100)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "idempotency_key"], name="unique_user_idempotency_key")]

    def __str__(self):
        return f"{self.mode} {self.id} ({self.status})"


class Order(models.Model):
    class Side(models.TextChoices):
        BUY = "BUY"
        SELL = "SELL"

    class Status(models.TextChoices):
        QUEUED = "QUEUED"
        PLACED = "PLACED"
        SUCCESS = "SUCCESS"
        PARTIAL = "PARTIAL"
        PENDING = "PENDING"
        FAILED = "FAILED"
        SKIPPED = "SKIPPED"

    execution = models.ForeignKey(Execution, on_delete=models.CASCADE, related_name="orders")
    symbol = models.CharField(max_length=30)
    side = models.CharField(max_length=4, choices=Side.choices)
    quantity = models.PositiveIntegerField()
    filled_quantity = models.PositiveIntegerField(default=0)
    sequence = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    tag = models.CharField(max_length=20, unique=True, default=new_order_tag)
    broker_order_id = models.CharField(max_length=64, blank=True)
    error_code = models.CharField(max_length=30, choices=ErrorCode.choices, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sequence"]

    def __str__(self):
        return f"{self.side} {self.quantity} {self.symbol} ({self.status})"
