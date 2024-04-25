from rest_framework.authentication import SessionAuthentication as _SessionAuthentication


class SessionAuthentication(_SessionAuthentication):
    """Custom session authentication class.

    This is a workaround for DRF returning 403 Forbidden status code instead
    of 401 Unauthorized for session authentication, that does not define
    an appropriate `WWW-Authenticate` header value.
    """

    def authenticate_header(self, request):
        return "Session"
