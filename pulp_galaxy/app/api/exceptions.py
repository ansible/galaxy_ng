import galaxy_pulp
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse

from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.settings import api_settings


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
    return Response(data, status=exc.status_code, headers=headers)


def _handle_api_client_exception(exc):
    return HttpResponse(exc.body, status=exc.status, content_type=exc.headers['Content-Type'])


def _handle_openapi_exception(exc, context=None):
    error = {'status': 400,
             'code': 'galaxy_pulp_api_error',
             'detail': str(exc)}

    data = {'errors': [error]}

    return Response(data, status=400)


def exception_handler(exc, context):
    """Custom exception handler."""
    if isinstance(exc, galaxy_pulp.ApiException):
        return _handle_api_client_exception(exc)

    if isinstance(exc, galaxy_pulp.OpenApiException):
        return _handle_openapi_exception(exc, context)

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.APIException):
        return _handle_drf_api_exception(exc)

    return None
