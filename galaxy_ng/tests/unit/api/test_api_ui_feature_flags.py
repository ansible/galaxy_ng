from django.conf import settings

from galaxy_ng.app.dynaconf_hooks import configure_feature_flags

from .base import BaseTestCase, get_current_ui_url


class TestUiFeatureFlagsView(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.original_setting = settings.GALAXY_FEATURE_FLAGS
        settings.GALAXY_FEATURE_FLAGS = {
            'execution_environments': True,
            'widget_x': False,
        }

    def tearDown(self):
        super().tearDown()
        settings.GALAXY_FEATURE_FLAGS = self.original_setting

    def test_feature_flags_url(self):
        self.feature_flags_url = get_current_ui_url('feature-flags')
        response = self.client.get(self.feature_flags_url)
        self.assertEqual(response.data['execution_environments'], True)
        self.assertEqual(response.data['widget_x'], False)

    def test_dynaconf_collection_signing_flag(self):
        data = configure_feature_flags(settings)
        self.assertEqual(data["GALAXY_FEATURE_FLAGS__collection_signing"], True)

        original_setting = settings.GALAXY_COLLECTION_SIGNING_SERVICE
        settings.GALAXY_COLLECTION_SIGNING_SERVICE = ""
        data = configure_feature_flags(settings)
        self.assertEqual(data["GALAXY_FEATURE_FLAGS__collection_signing"], False)
        settings.GALAXY_COLLECTION_SIGNING_SERVICE = original_setting
