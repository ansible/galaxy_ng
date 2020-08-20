from django.db import transaction
from rest_framework.authentication import BasicAuthentication
from rest_framework.request import Request
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status as http_code

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy


class TokenView(api_base.APIView):
    authentication_classes = (BasicAuthentication, *api_base.GALAXY_AUTHENTICATION_CLASSES)
    permission_classes = [access_policy.TokenAccessPolicy]

    @transaction.atomic
    def post(self, request: Request, *args, **kwargs) -> Response:
        """Create or refresh user token."""
        Token.objects.filter(user=self.request.user).delete()
        token = Token.objects.create(user=self.request.user)
        return Response({"token": token.key})

    def delete(self, request, *args, **kwargs):
        """Invalidate user token."""
        Token.objects.filter(user=self.request.user).delete()
        return Response(status=http_code.HTTP_204_NO_CONTENT)
