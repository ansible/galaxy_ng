from requests import post as requests_post

from django.conf import settings

from rest_framework.authentication import BasicAuthentication

from rest_framework import status as http_code
from rest_framework import exceptions

from social_django.utils import load_strategy
from social_core.backends.keycloak import KeycloakOAuth2

from gettext import gettext as _


class KeycloakBasicAuth(BasicAuthentication):
    def authenticate_credentials(self, userid, password, request=None):
        payload = {
            'client_id': settings.SOCIAL_AUTH_KEYCLOAK_KEY,
            'client_secret': settings.SOCIAL_AUTH_KEYCLOAK_SECRET,
            'grant_type': 'password',
            'scope': 'openid',
            'username': userid,
            'password': password
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = requests_post(
            url=settings.SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL,
            headers=headers,
            data=payload,
            verify=settings.GALAXY_VERIFY_KEYCLOAK_SSL_CERTS
        )

        if response.status_code == http_code.HTTP_200_OK:

            # load social auth django strategy
            strategy = load_strategy(request)
            backend = KeycloakOAuth2(strategy)

            token_data = backend.user_data(response.json()['access_token'])

            # The django social auth strategy uses data from the JWT token in the KeycloackOAuth2
            # backend to create a new user and update it with the data from the token. This
            # should return a django user instance.
            user = strategy.authenticate(backend, response=token_data)

            if user is None:
                raise exceptions.AuthenticationFailed(_("Authentication failed."))

            return (user, None)

        else:
            # If keycloak basic auth fails, try regular basic auth.
            return super().authenticate_credentials(userid, password, request)
