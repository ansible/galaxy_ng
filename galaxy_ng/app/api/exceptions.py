from django.core.exceptions import PermissionDenied
from django.http import Http404

from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.settings import api_settings


def _get_errors(detail, *, status, title, source=None, context=None):
    if isinstance(detail, list):
        for item in detail:
            yield from _get_errors(item, status=status, title=title, source=source, context=context)
    elif isinstance(detail, dict):
        for key, value in detail.items():
            yield from _get_errors(value, status=status, title=title, source=key, context=context)
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

        meta = {}

        # Provide the access_policy name to give a hint to origin of perm errors
        try:
            access_policy = context['access_policy']
            meta['access_policy'] = access_policy
        except KeyError:
            pass

        try:
            deployment_mode = context['deployment_mode']
            meta['deployment_mode'] = deployment_mode
        except KeyError:
            pass

        error['meta'] = meta

        yield error


def _handle_drf_api_exception(exc, context):
    headers = {}
    if getattr(exc, 'auth_header', None):
        headers['WWW-Authenticate'] = exc.auth_header
    if getattr(exc, 'wait', None):
        headers['Retry-After'] = '%d' % exc.wait

    title = exc.__class__.default_detail
    errors = _get_errors(exc.detail, status=exc.status_code, title=title, context=context)
    data = {'errors': list(errors)}
    return Response(data, status=exc.status_code, headers=headers)


def exception_handler(exc, context):
    """Custom exception handler."""

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    # Handle drf permission exceptions as drf exceptions extracting more detail
    elif isinstance(exc,
                    (exceptions.PermissionDenied,
                     exceptions.AuthenticationFailed,
                     exceptions.NotAuthenticated)):
        return _handle_drf_api_exception(exc, context)
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.APIException):
        return _handle_drf_api_exception(exc, context)

    return None
