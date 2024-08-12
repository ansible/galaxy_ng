from django.test import TestCase
from django.conf import settings
from ansible_base.lib.dynamic_config import dynamic_settings


DAB_REQUIRED_SETTINGS = [key for key in dir(dynamic_settings) if key.isupper()]

# FIXME ...
SKIP = [
    'ANSIBLE_BASE_OVERRIDABLE_SETTINGS',
    'ANSIBLE_BASE_OVERRIDDEN_SETTINGS',
    'OAUTH2_PROVIDER'
]
DAB_REQUIRED_SETTINGS = [x for x in DAB_REQUIRED_SETTINGS if x not in SKIP]


class TestSetting(TestCase):
    def test_dab_settings_are_loaded(self):
        """Ensure all required settings from DAB are configured on Galaxy"""
        notset = object()
        for key in DAB_REQUIRED_SETTINGS:
            key_on_galaxy = settings.get(key, notset)
            self.assertIsNot(key_on_galaxy, notset)
