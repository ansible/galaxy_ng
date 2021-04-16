import logging

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
