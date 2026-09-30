from django.contrib import admin

from brokers.models import BrokerAccount


@admin.register(BrokerAccount)
class BrokerAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "broker", "token_expires_at", "connected_at")
