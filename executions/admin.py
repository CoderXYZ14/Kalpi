from django.contrib import admin

from executions.models import Execution, Order


class OrderInline(admin.TabularInline):
    model = Order
    extra = 0


@admin.register(Execution)
class ExecutionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "mode", "status", "created_at", "finished_at")
    list_filter = ("mode", "status")
    inlines = [OrderInline]
