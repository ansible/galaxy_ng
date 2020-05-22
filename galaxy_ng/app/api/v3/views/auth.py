from django.contrib import auth as django_auth
from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

from galaxy_ng.app.api.base import GenericAPIView
from galaxy_ng.app.api.permissions import RestrictOnCloudDeployments
from galaxy_ng.app.api.v3.serializers import LoginSerializer
from galaxy_ng.app.models import User


class BaseLoginView(GenericAPIView):
    def _authenticate(self, request: Request) -> User:
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        user = django_auth.authenticate(
            request,
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        if user is None:
            raise PermissionDenied()
        return user


class LoginView(BaseLoginView):
    serializer_class = LoginSerializer
    permission_classes = (RestrictOnCloudDeployments,)

    def post(self, request: Request, *args, **kwargs) -> Response:
        user = self._authenticate(request)
        # Issue a token for a new user
        token = self._issue_token(user)
        return Response({
            "token": token.key,
        })

    @transaction.atomic
    def _issue_token(self, user):
        Token.objects.filter(user=user).delete()
        return Token.objects.create(user=user)
