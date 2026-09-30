import logging

from django.contrib.auth import get_user_model
from django.core import signing
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from brokers.adapters.registry import ADAPTERS, get_adapter
from brokers.errors import BrokerError
from brokers.models import BrokerAccount
from common.responses import error_response, success_response

logger = logging.getLogger("brokers")

STATE_SALT = "broker-login"
STATE_MAX_AGE = 600


def _unsupported(broker):
    return error_response(f"Unsupported broker '{broker}'. Supported: {', '.join(ADAPTERS)}", 400)


def _save_login(user, broker, result):
    BrokerAccount.objects.update_or_create(
        user=user,
        broker=broker,
        defaults={
            "access_token": result.access_token,
            "token_expires_at": result.expires_at,
            "connected_at": timezone.now(),
        },
    )
    logger.info("[login] user=%s broker=%s connected, expires %s", user.id, broker, result.expires_at)
    return {"broker": broker, "connected": True, "token_expires_at": result.expires_at}


class BrokerListView(APIView):
    def get(self, request):
        accounts = {account.broker: account for account in request.user.broker_accounts.all()}
        data = []
        for broker in ADAPTERS:
            account = accounts.get(broker)
            data.append({
                "broker": broker,
                "connected": bool(account and account.is_connected()),
                "token_expires_at": account.token_expires_at if account else None,
            })
        return success_response(data)


class BrokerLoginView(APIView):
    def get(self, request, broker):
        broker = broker.lower()
        if broker not in ADAPTERS:
            return _unsupported(broker)

        adapter = get_adapter(broker, user_id=request.user.id)
        state = signing.dumps({"user_id": request.user.id, "broker": broker}, salt=STATE_SALT)
        try:
            login_url = adapter.get_login_url(state)
            if login_url:
                return success_response({"broker": broker, "login_url": login_url})
            result = adapter.complete_login(request.query_params)
        except BrokerError as error:
            logger.warning("[login] user=%s broker=%s failed: %s", request.user.id, broker, error)
            return error_response(error.message, 400)
        return success_response(_save_login(request.user, broker, result))


class BrokerCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, broker):
        broker = broker.lower()
        if broker not in ADAPTERS:
            return _unsupported(broker)

        try:
            payload = signing.loads(request.query_params.get("state", ""), salt=STATE_SALT, max_age=STATE_MAX_AGE)
        except signing.BadSignature:
            return error_response("Login link is invalid or expired. Start login again.", 400)
        if payload["broker"] != broker:
            return error_response("Login state does not match this broker", 400)

        user = get_user_model().objects.filter(id=payload["user_id"], is_active=True).first()
        if user is None:
            return error_response("User for this login no longer exists or is inactive", 400)

        adapter = get_adapter(broker, user_id=user.id)
        try:
            result = adapter.complete_login(request.query_params)
        except BrokerError as error:
            logger.warning("[callback] user=%s broker=%s failed: %s", user.id, broker, error)
            return error_response(error.message, 400)
        return success_response(_save_login(user, broker, result))
