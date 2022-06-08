import logging

from django.conf import settings
from django.contrib import auth as django_auth
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.authentication import SessionAuthentication

from rest_framework.response import Response
from rest_framework import status as http_code

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app.api.ui.serializers import LoginSerializer

from requests import post as requests_post

log = logging.getLogger(__name__)

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

    def _oidc_logout(self, request):
        logout_url_str = "{keycloak}/auth/realms/{realm}/protocol/openid-connect/logout"
        logout_url = logout_url_str.format(keycloak=settings.KEYCLOAK_URL,
                                           realm=settings.KEYCLOAK_REALM)

        if not hasattr(request.user, 'social_auth'):
            return

        from social_django.models import UserSocialAuth
        try:
            social = request.user.social_auth.get(provider="keycloak")
        except UserSocialAuth.DoesNotExist:
            msg = "User does not have Social Auth object no openid-connect logout attemtped."
            log.warning(msg)
            return
        access_token = social.extra_data['access_token']
        refresh_token = social.extra_data['refresh_token']
        payload = {'client_id': settings.SOCIAL_AUTH_KEYCLOAK_KEY, 'refresh_token': refresh_token,
                   'client_secret': settings.SOCIAL_AUTH_KEYCLOAK_SECRET}
        headers = {"Authorization": "Bearer {access_token}".format(access_token=access_token)}
        response = requests_post(
            url=logout_url,
            headers=headers,
            data=payload,
            verify=settings.GALAXY_VERIFY_KEYCLOAK_SSL_CERTS
        )

        if response.status_code == http_code.HTTP_200_OK:
            log.debug("Logout of openid-connect client successful.")
        else:
            msg = "Log out for openid-connect failed with status {status} and content: {content}"
            log.warning(msg.format(status=response.status_code, content=response.text))

    def post(self, request, *args, **kwargs):
        # Trigger logout in Keycloak
        if settings.get("SOCIAL_AUTH_KEYCLOAK_KEY"):
            self._oidc_logout(request)

        django_auth.logout(request)
        return Response(status=http_code.HTTP_204_NO_CONTENT)
