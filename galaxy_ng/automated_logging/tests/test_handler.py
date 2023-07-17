# test max_age (rework?)
# test save
# test module removal
import logging
import logging.config
from datetime import timedelta
import time

from django.http import JsonResponse
from marshmallow import ValidationError

from automated_logging.helpers.exceptions import CouldNotConvertError
from automated_logging.models import ModelEvent, RequestEvent, UnspecifiedEvent
from automated_logging.tests.models import OrdinaryTest
from automated_logging.tests.base import BaseTestCase


class TestDatabaseHandlerTestCase(BaseTestCase):
    @staticmethod
    def view(request):
        return JsonResponse({})

    def test_max_age(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        duration = timedelta(seconds=1)
        logger = logging.getLogger(__name__)

        settings.AUTOMATED_LOGGING['model']['max_age'] = duration
        settings.AUTOMATED_LOGGING['request']['max_age'] = duration
        settings.AUTOMATED_LOGGING['unspecified']['max_age'] = duration

        conf.load.cache_clear()

        self.clear()
        self.bypass_request_restrictions()

        OrdinaryTest().save()
        self.request('GET', self.view)
        logger.info('I have the high ground Anakin!')

        self.assertEqual(ModelEvent.objects.count(), 1)
        self.assertEqual(RequestEvent.objects.count(), 1)
        self.assertEqual(UnspecifiedEvent.objects.count(), 1)

        time.sleep(2)

        logger.info('A surprise, to be sure, but a welcome one.')

        self.assertEqual(ModelEvent.objects.count(), 0)
        self.assertEqual(RequestEvent.objects.count(), 0)
        self.assertEqual(UnspecifiedEvent.objects.count(), 1)

    def test_max_age_input_methods(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        logger = logging.getLogger(__name__)

        settings.AUTOMATED_LOGGING['unspecified']['max_age'] = timedelta(seconds=1)
        conf.load.cache_clear()
        self.clear()

        logger.info('I will do what I must.')
        time.sleep(1)
        logger.info('Hello There.')
        self.assertEqual(UnspecifiedEvent.objects.count(), 1)

        settings.AUTOMATED_LOGGING['unspecified']['max_age'] = 1
        conf.load.cache_clear()
        self.clear()

        logger.info('A yes, the negotiator.')
        time.sleep(1)
        logger.info('Your tactics confuse and frighten me, sir.')
        self.assertEqual(UnspecifiedEvent.objects.count(), 1)

        settings.AUTOMATED_LOGGING['unspecified']['max_age'] = 'PT1S'
        conf.load.cache_clear()
        self.clear()

        logger.info('Don\'t make me kill you.')
        time.sleep(1)
        logger.info('An old friend from the dead.')
        self.assertEqual(UnspecifiedEvent.objects.count(), 1)

    def test_batching(self):
        from django.conf import settings

        logger = logging.getLogger(__name__)

        config = settings.LOGGING

        config['handlers']['db']['batch'] = 10
        logging.config.dictConfig(config)

        self.clear()
        for _ in range(9):
            logger.info('It\'s a trick. Send no reply')

        self.assertEqual(UnspecifiedEvent.objects.count(), 0)
        logger.info('I can\'t see a thing. My cockpit\'s fogging')
        self.assertEqual(UnspecifiedEvent.objects.count(), 10)

        config['handlers']['db']['batch'] = 1
        logging.config.dictConfig(config)
