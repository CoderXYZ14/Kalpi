from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken

from common.responses import success_response


class TokenView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        token, _ = Token.objects.get_or_create(user=serializer.validated_data["user"])
        return success_response({"token": token.key})
