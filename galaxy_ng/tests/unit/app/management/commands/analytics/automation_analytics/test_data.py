from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from pulpcore.app.views.status import StatusView

import galaxy_ng.app.metrics_collection.common_data


class TestHubVersion(SimpleTestCase):

    @patch('django.apps.apps.get_app_config')
    def test_hub_version_returns_galaxy_app_version(self, mock_get_app_config):
        mock_app_config = MagicMock()
        mock_app_config.version = "4.11.7"
        mock_get_app_config.return_value = mock_app_config

        result = galaxy_ng.app.metrics_collection.common_data.hub_version()

        mock_get_app_config.assert_called_with("galaxy")
        self.assertEqual(result, "4.11.7")


class TestAutomationAnalyticsData(TestCase):

    @patch('galaxy_ng.app.metrics_collection.common_data.StatusView.get')
    def test_api_status_request(self, mock_get):
        mocked_api_status = MagicMock(name="api_status")
        mock_get.return_value = MagicMock(status_code=200, data=mocked_api_status)

        response = galaxy_ng.app.metrics_collection.common_data.api_status()

        self.assertEqual(response, mocked_api_status)

        request = mock_get.call_args.args[0]
        self.assertEqual(request.method, 'GET')

    @override_settings(CACHE_ENABLED=False)
    @patch('pulpcore.app.views.status._disk_usage', return_value={
        'total': 1,
        'used': 1,
        'free': 0,
    })
    @patch.object(StatusView, '_get_db_conn_status', return_value=True)
    def test_api_status_direct_call(self, mock_db_status, mock_disk_usage):
        response = galaxy_ng.app.metrics_collection.common_data.api_status()

        self.assertEqual(response['database_connection'], {'connected': True})
        self.assertIn('versions', response)
        mock_db_status.assert_called_once_with()
        mock_disk_usage.assert_called_once_with()
