""" Test base every unit test uses """
import importlib
import logging.config
from copy import copy, deepcopy

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.test import TestCase, RequestFactory
from django.urls import path

from automated_logging.helpers import namedtuple2dict
from automated_logging.middleware import AutomatedLoggingMiddleware
from automated_logging.models import ModelEvent, RequestEvent, UnspecifiedEvent
from automated_logging.signals import cached_model_exclusion

User: AbstractUser = get_user_model()
USER_CREDENTIALS = {'username': 'example', 'password': 'example'}


def clear_cache():
    """ utility method to clear the cache """
    if hasattr(AutomatedLoggingMiddleware.thread, 'dal'):
        delattr(AutomatedLoggingMiddleware.thread, 'dal')

    import automated_logging.decorators

    # noinspection PyProtectedMember
    automated_logging.decorators._exclude_models.clear()
    # noinspection PyProtectedMember
    automated_logging.decorators._include_models.clear()

    cached_model_exclusion.cache_clear()


class BaseTestCase(TestCase):
    def __init__(self, method_name):
        from django.conf import settings

        settings.AUTOMATED_LOGGING_DEV = True

        super().__init__(method_name)

    def request(self, method, view, data=None):
        """
        request a specific view and return the response.

        This is not ideal and super hacky. Backups the actual urlpatterns,
        and then overrides the urlpatterns with a temporary one and then
        inserts the new one again.
        """

        urlconf = importlib.import_module(settings.ROOT_URLCONF)

        backup = copy(urlconf.urlpatterns)
        urlconf.urlpatterns.clear()
        urlconf.urlpatterns.append(path('', view))

        response = self.client.generic(method, '/', data=data)

        urlconf.urlpatterns.clear()
        urlconf.urlpatterns.extend(backup)

        return response

    def setUp(self):
        """ setUp the DAL specific test environment """
        from django.conf import settings
        from automated_logging.settings import default, settings as conf

        self.user = User.objects.create_user(**USER_CREDENTIALS)
        self.user.save()

        self.original_config = deepcopy(settings.AUTOMATED_LOGGING)

        base = namedtuple2dict(default)

        settings.AUTOMATED_LOGGING.clear()
        for key, value in base.items():
            settings.AUTOMATED_LOGGING[key] = deepcopy(value)

        conf.load.cache_clear()

        self.setUpLogging()
        super().setUp()

    def tearDown(self) -> None:
        """ tearDown the DAL specific environment """
        from django.conf import settings
        from automated_logging.settings import settings as conf

        super().tearDown()

        self.tearDownLogging()

        settings.AUTOMATED_LOGGING.clear()
        for key, value in self.original_config.items():
            settings.AUTOMATED_LOGGING[key] = deepcopy(value)

        conf.load.cache_clear()

        clear_cache()

    @staticmethod
    def clear():
        """ clear all events """
        ModelEvent.objects.all().delete()
        RequestEvent.objects.all().delete()
        UnspecifiedEvent.objects.all().delete()

    def tearDownLogging(self):
        """
        replace our own logging config
        with the original to not break any other tests
        that might depend on it.
        """
        from django.conf import settings

        settings.LOGGING = self.logging_backup
        logging.config.dictConfig(settings.LOGGING)

    def setUpLogging(self):
        """ sets up logging dict, so that we can actually use our own """
        from django.conf import settings

        self.logging_backup = deepcopy(settings.LOGGING)
        settings.LOGGING = {
            'version': 1,
            'disable_existing_loggers': False,
            'root': {'level': 'INFO', 'handlers': ['console', 'db'],},
            'formatters': {
                'verbose': {
                    'format': '%(levelname)s %(asctime)s %(module)s '
                    '%(process)d %(thread)d %(message)s'
                },
                'simple': {'format': '%(levelname)s %(message)s'},
                'syslog': {
                    'format': '%(asctime)s %%LOCAL0-%(levelname) %(message)s'
                    # 'format': '%(levelname)s %(message)s'
                },
            },
            'handlers': {
                'console': {
                    'level': 'INFO',
                    'class': 'logging.StreamHandler',
                    'formatter': 'verbose',
                },
                'db': {
                    'level': 'INFO',
                    'class': 'automated_logging.handlers.DatabaseHandler',
                },
            },
            'loggers': {
                'automated_logging': {
                    'level': 'INFO',
                    'handlers': ['console', 'db'],
                    'propagate': False,
                },
                'django': {
                    'level': 'INFO',
                    'handlers': ['console', 'db'],
                    'propagate': False,
                },
            },
        }

        logging.config.dictConfig(settings.LOGGING)

    def bypass_request_restrictions(self):
        """ bypass all request default restrictions of DAL """
        from django.conf import settings
        from automated_logging.settings import settings as conf

        settings.AUTOMATED_LOGGING['request']['exclude']['status'] = []
        settings.AUTOMATED_LOGGING['request']['exclude']['methods'] = []
        conf.load.cache_clear()

        self.clear()
