"""Authentication helpers for the container registry token endpoint.

Podman and other registry clients always send credentials to ``/v2/auth/token``
using HTTP Basic authentication.  DRF's ``TokenAuthentication`` expects an
``Authorization: Token <key>`` header instead, so an API token supplied as the
Basic password can never authenticate.  That was previously masked for public
execution environments because anonymous pulls were allowed; once pulls require
authentication, token based automation needs to keep working.

``BasicOrTokenPasswordAuthentication`` accepts either a real password or an
API token in the Basic password field.  It is installed in front of the
standard ``BasicAuthentication`` on ``pulp_container``'s ``BearerTokenView``.
"""

from django.contrib.auth import authenticate
from rest_framework.authentication import BasicAuthentication
from rest_framework.authtoken.models import Token


class BasicOrTokenPasswordAuthentication(BasicAuthentication):
    """Authenticate Basic credentials whose password may be an API token.

    A real username/password pair is tried first so existing password logins
    keep their exact behaviour.  If that fails, the password is looked up as a
    DRF API token and accepted only when it belongs to the supplied username.
    Returning ``None`` hands the request back to the next authenticator, which
    preserves the normal ``401`` for genuinely invalid credentials.
    """

    def authenticate_credentials(self, userid, password, request=None):
        user = authenticate(request=request, username=userid, password=password)
        if user is not None:
            return (user, None)

        token = Token.objects.select_related("user").filter(key=password).first()
        if token and token.user.get_username() == userid and token.user.is_active:
            return (token.user, token)

        return None


def enable_registry_token_password_auth():
    """Allow API tokens to be used as registry Basic-auth passwords.

    Must run during app startup, before requests are served.  The BearerTokenView
    inherits DRF's default authentication classes, so prepending our class is
    enough to handle password and token logins in the same Basic-auth header.
    """

    from pulp_container.app.registry_api import BearerTokenView

    authentication_classes = list(BearerTokenView.authentication_classes)
    if BasicOrTokenPasswordAuthentication in authentication_classes:
        return

    BearerTokenView.authentication_classes = [
        BasicOrTokenPasswordAuthentication,
        *authentication_classes,
    ]
