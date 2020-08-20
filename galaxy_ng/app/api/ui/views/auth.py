from django.contrib import auth as django_auth
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.authentication import SessionAuthentication

from rest_framework.response import Response
from rest_framework import status as http_code

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy


from galaxy_ng.app.api.ui.serializers import LoginSerializer


__all__ = (
    "LoginView",
    "LogoutView",
)


class _CSRFSessionAuthentication(SessionAuthentication):
    """CSRF-enforcing version of a SessionAuthentication class."""

    def authenticate(self, request):
        user = getattr(request._request, "user", None)
        self.enforce_csrf(request)
        return user, None


class LoginView(api_base.GenericAPIView):
    serializer_class = LoginSerializer
    authentication_classes = (_CSRFSessionAuthentication,)
    permission_classes = [access_policy.LoginAccessPolicy]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        return Response(status=http_code.HTTP_204_NO_CONTENT)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = django_auth.authenticate(request, username=username, password=password)
        if user is None:
            return Response(status=http_code.HTTP_403_FORBIDDEN)

        django_auth.login(request, user)
        return Response(status=http_code.HTTP_204_NO_CONTENT)


class LogoutView(api_base.APIView):
    permission_classes = [access_policy.LogoutAccessPolicy]

    def post(self, request, *args, **kwargs):
        django_auth.logout(request)
        return Response(status=http_code.HTTP_204_NO_CONTENT)
