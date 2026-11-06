from django.conf import settings

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

    def test_unauthenticated_user_gets_authentication_feature_flags(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(get_current_ui_url('feature-flags'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.data),
            {'dab_resource_registry', 'external_authentication'},
        )
        self.assertEqual(response["Cache-Control"], "private")
        self.assertIn("Authorization", response["Vary"])
        self.assertIn("Cookie", response["Vary"])

    def _get_feature_flags(self, flags, **setting_values):
        original_flags = settings.GALAXY_FEATURE_FLAGS
        original_settings = {
            key: getattr(settings, key, None) for key in setting_values
        }
        settings.GALAXY_FEATURE_FLAGS = flags
        for key, value in setting_values.items():
            setattr(settings, key, value)

        try:
            return self.client.get(get_current_ui_url('feature-flags'))
        finally:
            settings.GALAXY_FEATURE_FLAGS = original_flags
            for key, value in original_settings.items():
                setattr(settings, key, value)

    def test_signing_configuration_warnings(self):
        response = self._get_feature_flags(
            {}, GALAXY_COLLECTION_SIGNING_SERVICE='missing'
        )
        self.assertTrue(response.data['_messages'])

        response = self._get_feature_flags(
            {'signatures_enabled': True, 'collection_auto_sign': True},
            GALAXY_COLLECTION_SIGNING_SERVICE='missing',
            GALAXY_CONTAINER_SIGNING_SERVICE=None,
        )
        self.assertEqual(len(response.data['_messages']), 2)

        response = self._get_feature_flags(
            {
                'signatures_enabled': True,
                'display_signatures': True,
                'can_create_signatures': False,
                'can_upload_signatures': False,
            }
        )
        self.assertTrue(response.data['_messages'])

        response = self._get_feature_flags(
            {'execution_environments': True},
            GALAXY_CONTAINER_SIGNING_SERVICE='missing',
        )
        self.assertTrue(response.data['_messages'])

        response = self._get_feature_flags(
            {'container_signing': True},
            GALAXY_CONTAINER_SIGNING_SERVICE='missing',
        )
        self.assertEqual(len(response.data['_messages']), 2)
