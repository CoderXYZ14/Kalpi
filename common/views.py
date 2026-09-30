from django.http import JsonResponse
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.throttling import AnonRateThrottle

from common.responses import success_response


class TokenView(ObtainAuthToken):
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        token, _ = Token.objects.get_or_create(user=serializer.validated_data["user"])
        return success_response({"token": token.key})


def not_found(request, exception=None):
    return JsonResponse({"success": False, "error": "Not found"}, status=404)


def server_error(request):
    return JsonResponse({"success": False, "error": "Internal server error"}, status=500)
