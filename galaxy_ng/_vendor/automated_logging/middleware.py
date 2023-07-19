import logging
import threading
from typing import NamedTuple, Optional, TYPE_CHECKING

from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

RequestInformation = NamedTuple(
    'RequestInformation',
    [
        ('request', HttpRequest),
        ('response', Optional[HttpResponse]),
        ('exception', Optional[Exception]),
    ],
)


class AutomatedLoggingMiddleware:
    """
    Middleware used by django-automated-logging
    to provide request specific data to the request signals via
    the local thread.
    """

    thread = threading.local()

    def __init__(self, get_response):
        self.get_response = get_response

        AutomatedLoggingMiddleware.thread.__dal__ = None

    @staticmethod
    def save(request, response=None, exception=None):
        """
        Helper middleware, that sadly needs to be present.
        the request_finished and request_started signals only
        expose the class, not the actual request and response.

        We save the request and response specific data in the thread.

        :param request: Django Request
        :param response: Optional Django Response
        :param exception: Optional Exception
        :return:
        """

        AutomatedLoggingMiddleware.thread.__dal__ = RequestInformation(
            request, response, exception
        )

    def __call__(self, request):
        """
        TODO: fix staticfiles has no environment?!
        it seems like middleware isn't getting called for serving the static files,
        this seems very odd.

        There are 2 different states, request object will be stored when available
        and response will only be available post get_response.

        :param request:
        :return:
        """
        self.save(request)

        response = self.get_response(request)

        self.save(request, response)

        return response

    def process_exception(self, request, exception):
        """
        Exception proceeds the same as __call__ and therefore should
        also save things in the local thread.

        :param request: Django Request
        :param exception: Thrown Exception
        :return: -
        """
        self.save(request, exception=exception)

    @staticmethod
    def cleanup():
        """
        Cleanup function, that should be called last. Overwrites the
        custom __dal__ object with None, to make sure the next request
        does not use the same object.

        :return: -
        """
        AutomatedLoggingMiddleware.thread.__dal__ = None

    @staticmethod
    def get_current_environ() -> Optional[RequestInformation]:
        """
        Helper staticmethod that looks if the __dal__ custom attribute
        is present and returns either the attribute or None

        :return: Optional[RequestInformation]
        """

        if getattr(AutomatedLoggingMiddleware.thread, '__dal__', None):
            return RequestInformation(*AutomatedLoggingMiddleware.thread.__dal__)

        return None

    @staticmethod
    def get_current_user(
        environ: RequestInformation = None,
    ) -> Optional['AbstractUser']:
        """
        Helper staticmethod that returns the current user, taken from
        the current environment.

        :return: Optional[User]
        """
        from django.contrib.auth.models import AnonymousUser

        if not environ:
            environ = AutomatedLoggingMiddleware.get_current_environ()

        if not environ:
            return None

        if isinstance(environ.request.user, AnonymousUser):
            return None

        return environ.request.user
