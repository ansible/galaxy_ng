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
