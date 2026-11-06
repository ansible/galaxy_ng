from django.conf import settings
from django.test import override_settings

from .base import BaseTestCase, get_current_ui_url


class TestUiSettingsView(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.original_setting = settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS
        self.original_download_setting = (
            settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD
        )
        settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS = True

    def tearDown(self):
        super().tearDown()
        settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS = self.original_setting
        settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD = self.original_download_setting

    def test_settings_url(self):
        self.settings_url = get_current_ui_url('settings')
        response = self.client.get(self.settings_url)
        self.assertEqual(response.data['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS'], True)
        self.assertEqual(response.data['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD'], False)
        self.assertIn('GALAXY_FEATURE_FLAGS', response.data)

    def test_unauthenticated_user_gets_public_settings(self):
        self.client.force_authenticate(user=None)
        with override_settings(
            GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS=False,
            GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD=True,
        ):
            response = self.client.get(get_current_ui_url('settings'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                'GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS': False,
                'GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD': True,
            },
        )
        self.assertEqual(response["Cache-Control"], "private")
        self.assertIn("Authorization", response["Vary"])
        self.assertIn("Cookie", response["Vary"])
