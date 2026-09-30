from django.conf import settings
from django.db import models
from django.utils import timezone


class BrokerAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="broker_accounts")
    broker = models.CharField(max_length=20)
    access_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "broker"], name="unique_user_broker")]

    def __str__(self):
        return f"{self.user} - {self.broker}"

    def is_connected(self):
        return bool(self.access_token) and self.token_expires_at is not None and self.token_expires_at > timezone.now()
