from django.conf import settings

from .base import BaseTestCase, get_current_ui_url


class TestUiFeatureFlagsView(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.original_setting = settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS
        settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS = True

    def tearDown(self):
        super().tearDown()
        settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS = self.original_setting

    def test_settings_url(self):
        self.settings_url = get_current_ui_url('settings')
        response = self.client.get(self.settings_url)
        self.assertEqual(response.data['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS'], True)
        self.assertEqual(response.data['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD'], False)
