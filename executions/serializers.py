import re
from collections import Counter

from rest_framework import serializers

from brokers.adapters.registry import ADAPTERS
from executions.engine import normalize
from executions.models import Execution, Order

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9&-]{1,30}$")
MAX_ORDERS = 100


def clean_symbol(value):
    symbol = value.strip().upper()
    if not SYMBOL_PATTERN.match(symbol):
        raise serializers.ValidationError(f"'{value}' is not a valid NSE symbol")
    return symbol


class OrderItemSerializer(serializers.Serializer):
    symbol = serializers.CharField()
    quantity = serializers.IntegerField(
        min_value=1,
        error_messages={
            "min_value": "INVALID_QUANTITY: must be a positive whole number",
            "invalid": "INVALID_QUANTITY: must be a positive whole number",
        },
    )

    def validate_symbol(self, value):
        return clean_symbol(value)


class RebalanceItemSerializer(serializers.Serializer):
    symbol = serializers.CharField()
    quantity_change = serializers.IntegerField(error_messages={"invalid": "INVALID_QUANTITY: must be a whole number"})

    def validate_symbol(self, value):
        return clean_symbol(value)


class ExecutionCreateSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=Execution.Mode.choices)
    broker = serializers.CharField()
    idempotency_key = serializers.CharField(max_length=100)
    buy = OrderItemSerializer(many=True, required=False, default=list)
    sell = OrderItemSerializer(many=True, required=False, default=list)
    rebalance = RebalanceItemSerializer(many=True, required=False, default=list)

    def validate_broker(self, value):
        broker = value.strip().lower()
        if broker not in ADAPTERS:
            raise serializers.ValidationError(f"Unsupported broker '{value}'. Supported: {', '.join(ADAPTERS)}")
        return broker

    def validate(self, data):
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(f"Unknown fields: {', '.join(sorted(unknown))}")

        if data["mode"] == Execution.Mode.FIRST_TIME and (data["sell"] or data["rebalance"]):
            raise serializers.ValidationError("FIRST_TIME only accepts 'buy'. Use REBALANCE for sell/rebalance.")

        symbols = [item["symbol"] for group in ("sell", "buy", "rebalance") for item in data[group]]
        duplicates = sorted(symbol for symbol, count in Counter(symbols).items() if count > 1)
        if duplicates:
            raise serializers.ValidationError(f"Each symbol can appear only once per request. Duplicates: {', '.join(duplicates)}")

        orders = normalize(data)
        if not orders:
            raise serializers.ValidationError("Nothing to execute: no buy/sell orders and no non-zero rebalance changes")
        if len(orders) > MAX_ORDERS:
            raise serializers.ValidationError(f"Too many orders ({len(orders)}). Max {MAX_ORDERS} per execution.")

        data["orders"] = orders
        return data


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "sequence", "symbol", "side", "quantity", "filled_quantity", "status",
            "tag", "broker_order_id", "error_code", "error_message", "updated_at",
        ]


class ExecutionSerializer(serializers.ModelSerializer):
    broker = serializers.CharField(source="broker_account.broker")
    counts = serializers.SerializerMethodField()
    orders = OrderSerializer(many=True)

    class Meta:
        model = Execution
        fields = [
            "id", "mode", "broker", "status", "idempotency_key", "error_message",
            "created_at", "finished_at", "counts", "orders",
        ]

    def get_counts(self, execution):
        return dict(Counter(order.status for order in execution.orders.all()))
