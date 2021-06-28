from django.core.exceptions import PermissionDenied
from django.http import Http404

from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.settings import api_settings

import logging
log = logging.getLogger(__name__)


def _get_errors(detail, *, status, title, source=None):
    if isinstance(detail, list):
        for item in detail:
            yield from _get_errors(item, status=status, title=title, source=source)
    elif isinstance(detail, dict):
        for key, value in detail.items():
            yield from _get_errors(value, status=status, title=title, source=key)
    else:
        error = {
            'status': str(status),
            'code': detail.code,
            'title': title,
        }

        if title != detail:
            error['detail'] = str(detail)
        if source and source != api_settings.NON_FIELD_ERRORS_KEY:
            error['source'] = {'parameter': source}

        yield error


def _handle_drf_api_exception(exc):
    headers = {}
    if getattr(exc, 'auth_header', None):
        headers['WWW-Authenticate'] = exc.auth_header
    if getattr(exc, 'wait', None):
        headers['Retry-After'] = '%d' % exc.wait

    title = exc.__class__.default_detail
    errors = _get_errors(exc.detail, status=exc.status_code, title=title)
    data = {'errors': list(errors)}
    log.debug('exc data: %s', data)
    return Response(data, status=exc.status_code, headers=headers)


def exception_handler(exc, context):
    """Custom exception handler."""

    if isinstance(exc, Http404):
        log.debug('exc: %s', exc)
        log.debug('exc: %r', exc)
        log.debug('context: %s', context)
        try:
            raise exceptions.NotFound() from exc
        except exceptions.NotFound as raised:
            exc = raised
            log.debug('exc: %s', exc)
            log.debug('exc: %r', exc)
            log.exception(exc)
        #new_exc = exceptions.NotFound()
        #new_exc.__context__ = exc
        #exc = new_exc
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.APIException):
        return _handle_drf_api_exception(exc)

    return None
