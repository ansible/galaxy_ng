from django.conf import settings

from galaxy_ng.app import dynaconf_hooks

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
        original_setting = settings.GALAXY_COLLECTION_SIGNING_SERVICE

        for dynaconf_func in [dynaconf_hooks.configure_feature_flags, dynaconf_hooks.post]:
            settings.GALAXY_COLLECTION_SIGNING_SERVICE = "my-signing-service"
            data = dynaconf_func(settings)
            self.assertEqual(data["GALAXY_FEATURE_FLAGS__collection_signing"], True)

            settings.GALAXY_COLLECTION_SIGNING_SERVICE = ""
            data = dynaconf_func(settings)
            self.assertEqual(data["GALAXY_FEATURE_FLAGS__collection_signing"], False)

            settings.GALAXY_COLLECTION_SIGNING_SERVICE = original_setting
