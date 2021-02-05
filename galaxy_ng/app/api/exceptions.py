from django.core.exceptions import PermissionDenied
from django.http import Http404

from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.settings import api_settings


class AccessPolicyPermissionDenied(exceptions.PermissionDenied):
    def __init__(self, detail=None, code=None, permission=None):
        self.permission = permission
        super().__init__(detail, code)


def _get_errors(detail, *, status, title, source=None, context=None):
    """Generator which returns JSON:API style error structs for use in the REST responses.

    See https://jsonapi.org/format/#errors for details on the JSON:API Error format
    including the valid, required, and optional fields.

    This also handles a couple different ways the exception 'detail' may be structured,
    including a 'detail' struct, a list of 'detail' structs, or a dict whose key is
    the 'source' of the error and the value is a 'detail' struct (which may also be any
    of the forms mentioned).

    The 'detail' struct is recursively processed if the 'detail' has nested 'detail' structs.

    JSON:API provides an option 'meta' field in the Error's in the REST response.
    We populate the following fields of the 'meta' dict:
        - access_policy -> {'name': 'UserViewSet',...}
        - deployment_mode -> the GALAXY_DEPLOYMENT_MODE setting as a string

    """

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
            # access_policy = context['permission']['access_policy']
            permission = context['permission']
            if permission:
                statements = permission.get_policy_statements(context['request'],
                                                              context['view'])

                meta['access_policy'] = {'name': permission.NAME,
                                         'failed_rules': permission.matched,
                                         'statements': statements}

        except KeyError:
            pass

        try:
            deployment_mode = context['deployment_mode']
            meta['deployment_mode'] = deployment_mode
        except KeyError:
            pass

        # TODO: We could add other context info here. We have the Request and View objects and
        #       the request args/kwargs so lots of potential.
        # - client and server application versions
        # - a request_id (will be in headers, but may be more useful if also included in the body)
        # - an 'access_policy' version (or if,checksum, data, etc)
        # - a point to an issue tracker url to file a ticket (for ex, a standalone may point to
        #   an internal remedy system, etc). Though the Error object can have a
        #   'links' field with a link that points to "further details about this
        #    particular occurrence of the problem."

        error['meta'] = meta

        yield error


def _handle_drf_api_exception(exc, context):
    headers = {}
    if getattr(exc, 'auth_header', None):
        headers['WWW-Authenticate'] = exc.auth_header
    if getattr(exc, 'wait', None):
        headers['Retry-After'] = '%d' % exc.wait

    # Build a list of JSON:API style error objects
    title = exc.__class__.default_detail
    context['permission'] = getattr(exc, 'permission', [])
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
    # regular django PermissionDenied for not drf endpoints
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.APIException):
        return _handle_drf_api_exception(exc, context)

    return None
