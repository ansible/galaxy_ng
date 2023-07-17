from datetime import timedelta

from marshmallow import ValidationError

from automated_logging.signals import _function_model_exclusion
from automated_logging.tests.base import BaseTestCase


class MiscellaneousTestCase(BaseTestCase):
    def test_no_sender(self):
        self.assertIsNone(_function_model_exclusion(None, '', ''))

    def test_wrong_duration(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        settings.AUTOMATED_LOGGING['unspecified']['max_age'] = complex(1, 1)
        conf.load.cache_clear()
        self.clear()

        self.assertRaises(ValidationError, conf.load)

        settings.AUTOMATED_LOGGING['unspecified']['max_age'] = (
            timedelta.max.total_seconds() + 1
        )
        conf.load.cache_clear()
        self.clear()

        self.assertRaises(ValidationError, conf.load)

        settings.AUTOMATED_LOGGING['unspecified']['max_age'] = 'Haha, error go brrr'
        conf.load.cache_clear()
        self.clear()

        self.assertRaises(ValidationError, conf.load)

    def test_unsupported_search_string(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        settings.AUTOMATED_LOGGING['unspecified']['exclude']['applications'] = [
            'te:abc'
        ]
        conf.load.cache_clear()
        self.clear()

        self.assertRaises(ValidationError, conf.load)

        # settings.AUTOMATED_LOGGING['unspecified']['exclude']['applications'] = []
        conf.load.cache_clear()
        self.clear()

    def test_duration_none(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        settings.AUTOMATED_LOGGING['unspecified']['max_age'] = None
        conf.load.cache_clear()
        self.clear()

        self.assertIsNone(conf.unspecified.max_age)
