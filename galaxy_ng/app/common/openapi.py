import logging

log = logging.getLogger(__name__)
log.debug('openapi autoschema')


def preprocess_debug_logger(endpoints, **kwargs):
    """Return an iterable of (path, path_regex, method, callback) tuples"""

    log.debug("kwargs: %s", repr(kwargs))

    return [
        (path, path_regex, method, callback) for path, path_regex, method, callback in endpoints
        if not log.debug('path=%s, path_regex=%s, methos=%s, callback=%s',
                         path, path_regex, method, callback)
    ]


def preprocess_exclude_pulp_endpoints(endpoints, **kwargs):
    """Return an iterable of (path, path_regex, method, callback) with /pulp* endpoints removed"""

    return [
        (path, path_regex, method, callback) for path, path_regex, method, callback in endpoints
        if not path.startswith('/pulp')
    ]
