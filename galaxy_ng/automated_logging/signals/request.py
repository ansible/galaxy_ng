"""
File handles the processing and redirection of all request related
signals
"""

import logging
import urllib.parse

from django.core.handlers.wsgi import WSGIRequest
from django.dispatch import receiver
from django.core.signals import got_request_exception, request_finished
from django.http import Http404, JsonResponse
from django.urls import resolve

from automated_logging.middleware import AutomatedLoggingMiddleware
from automated_logging.models import RequestEvent, Application, RequestContext
from automated_logging.settings import settings
from automated_logging.signals import request_exclusion

# TODO: should django-ipware be optional?
try:
    from ipware import get_client_ip
except ImportError:
    get_client_ip = None


logger = logging.getLogger(__name__)


@receiver(request_finished, weak=False)
def request_finished_signal(sender, **kwargs) -> None:
    """
    This signal gets the environment from the local thread and
    sends a logging message, that message will be processed by the
    handler later on.

    This is a simple redirection.

    :return: -
    """
    level = settings.request.loglevel
    environ = AutomatedLoggingMiddleware.get_current_environ()

    if not environ:
        if settings.request.log_request_was_not_recorded:
            logger.info(
                "Environment for request couldn't be determined. "
                "Request was not recorded."
            )
        return

    request = RequestEvent()

    request.user = AutomatedLoggingMiddleware.get_current_user(environ)
    request.uri = environ.request.get_full_path()

    if not settings.request.data.query:
        request.uri = urllib.parse.urlparse(request.uri).path

    if 'request' in settings.request.data.enabled:
        request_context = RequestContext()
        request_context.content = environ.request.body
        request_context.type = environ.request.content_type

        request.request = request_context

    if 'response' in settings.request.data.enabled:
        response_context = RequestContext()
        response_context.content = environ.response.content
        response_context.type = environ.response['Content-Type']

        request.response = response_context

    # TODO: context parsing, masking and removal
    if get_client_ip and settings.request.ip:
        request.ip, _ = get_client_ip(environ.request)

    request.status = environ.response.status_code if environ.response else None
    request.method = environ.request.method.upper()
    request.context_type = environ.request.content_type

    try:
        function = resolve(environ.request.path).func
    except Http404:
        function = None

    request.application = Application(name=None)
    if function:
        application = function.__module__.split('.')[0]
        request.application = Application(name=application)

    if request_exclusion(request, function):
        return
    
    logger_ip = f' from {request.ip}' if get_client_ip and settings.request.ip else ''
    logger.log(
        level,
        f'[{request.method}] [{request.status}] '
        f'{getattr(request, "user", None) or "Anonymous"} '
        f'at {request.uri}{logger_ip}',
        extra={'action': 'request', 'event': request},
    )


@receiver(got_request_exception, weak=False)
def request_exception(sender, request, **kwargs):
    """
    Exception logging for requests, via the django signal.

    The signal can also return a WSGIRequest exception, which does not
    have all fields that are needed.

    :return: -
    """

    status = int(request.status_code) if hasattr(request, 'status_code') else None
    method = request.method if hasattr(request, 'method') else None
    reason = request.reason_phrase if hasattr(request, 'reason_phrase') else None
    level = logging.CRITICAL if status and status <= 500 else logging.WARNING

    is_wsgi = isinstance(request, WSGIRequest)

    logger.log(
        level,
        f'[{method or "UNK"}] [{status or "UNK"}] '
        f'{is_wsgi and "[WSGIResponse] "}'
        f'Exception: {reason or "UNKNOWN"}',
    )


@receiver(request_finished, weak=False)
def thread_cleanup(sender, **kwargs):
    """
    This signal just calls the thread cleanup function to make sure,
    that the custom thread object is always clean for the next request.
    This needs to be always the last function registered by the receiver!

    :return: -
    """
    AutomatedLoggingMiddleware.cleanup()
