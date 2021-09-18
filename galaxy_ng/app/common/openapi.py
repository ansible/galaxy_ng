import logging

from django.conf import settings

log = logging.getLogger(__name__)
log.debug('openapi autoschema')


def preprocess_debug_logger(endpoints, **kwargs):
    """Log and then return an iterable of (path, path_regex, method, callback) tuples"""

    log.debug("kwargs: %s", repr(kwargs))

    for path, path_regex, method, callback in endpoints:
        log.debug('path=%s, path_regex=%s, method=%s, callback=%s',
                  path, path_regex, method, callback)

    return endpoints
    # return [
    #     (path, path_regex, method, callback) for path, path_regex, method, callback in endpoints
    #     if log.debug('path=%s, path_regex=%s, method=%s, callback=%s',
    #                  path, path_regex, method, callback)
    # ]


def preprocess_exclude_endpoints(endpoints, **kwargs):
    """Return an iterable of (path, path_regex, method, callback) with some endpoints removed

    For example, the default is to to remove '/pulp' and '/_ui/' api endpoints, while
    allowing /pulp/api/v3/status endpoint and all automation-hub v3 endpoints.
    """
    return [
        (path, path_regex, method, callback) for path, path_regex, method, callback in endpoints
        if path == '/pulp/api/v3/status/' or (not path.startswith('/pulp') and '/_ui/' not in path)
    ]


class AllowCorsMiddleware:
    """This is for use on dev environment and testing only"""

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)
        response["Access-Control-Allow-Origin"] = settings.get("GALAXY_CORS_ALLOWED_ORIGINS", "")
        response["Access-Control-Allow-Headers"] = settings.get("GALAXY_CORS_ALLOWED_HEADERS", "")

        # Code to be executed for each request/response after
        # the view is called.

        return response
