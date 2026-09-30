import logging
import uuid

from django.db import IntegrityError, transaction
from rest_framework.views import APIView

from brokers.models import BrokerAccount
from common.responses import error_response, success_response
from executions.engine import start_execution
from executions.models import Execution, Order
from executions.serializers import ExecutionCreateSerializer, ExecutionSerializer

logger = logging.getLogger("executions")


def _existing(user, idempotency_key):
    return Execution.objects.filter(user=user, idempotency_key=idempotency_key).first()


class ExecutionCreateView(APIView):
    def post(self, request):
        serializer = ExecutionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        existing = _existing(request.user, data["idempotency_key"])
        if existing:
            logger.info("[create] user=%s reused idempotency_key=%s -> %s", request.user.id, data["idempotency_key"], existing.id)
            return success_response(ExecutionSerializer(existing).data)

        account = BrokerAccount.objects.filter(user=request.user, broker=data["broker"]).first()
        if account is None:
            return error_response(f"Connect {data['broker']} first: GET /api/brokers/{data['broker']}/login/", 400)

        try:
            with transaction.atomic():
                execution = Execution.objects.create(
                    user=request.user,
                    broker_account=account,
                    mode=data["mode"],
                    idempotency_key=data["idempotency_key"],
                )
                Order.objects.bulk_create([
                    Order(execution=execution, symbol=symbol, side=side, quantity=quantity, sequence=sequence)
                    for sequence, (symbol, side, quantity) in enumerate(data["orders"], start=1)
                ])
        except IntegrityError:
            existing = _existing(request.user, data["idempotency_key"])
            if existing:
                return success_response(ExecutionSerializer(existing).data)
            return error_response(f"An execution is already running on {data['broker']}. Wait for it to finish.", 409)

        logger.info("[create] user=%s execution=%s mode=%s orders=%d", request.user.id, execution.id, execution.mode, len(data["orders"]))
        transaction.on_commit(lambda: start_execution(execution.id))
        return success_response({"execution_id": str(execution.id), "status": execution.status}, 202)


class ExecutionDetailView(APIView):
    def get(self, request, execution_id):
        try:
            execution_uuid = uuid.UUID(execution_id)
        except ValueError:
            return error_response("Execution not found", 404)

        execution = (
            Execution.objects.select_related("broker_account")
            .prefetch_related("orders")
            .filter(id=execution_uuid, user=request.user)
            .first()
        )
        if execution is None:
            return error_response("Execution not found", 404)
        return success_response(ExecutionSerializer(execution).data)
