import galaxy_ng.app.metrics_collection.common_data
from django.test import TestCase, override_settings
from unittest.mock import MagicMock, patch
import unittest


class TestAutomationAnalyticsData(TestCase):

    @unittest.skip("FIXME - broken by dab 2024.12.13")
    @override_settings(ANSIBLE_API_HOSTNAME='https://example.com')
    @override_settings(GALAXY_API_PATH_PREFIX='/api-test/xxx')
    @patch('galaxy_ng.app.metrics_collection.common_data.requests.request')
    def test_api_status_request(self, mock_request):
        mock_response = MagicMock(name="mock_response")
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        json_response = MagicMock(name="json")
        mocked_api_status = MagicMock(name="api_status")
        json_response.return_value = mocked_api_status
        mock_response.json = json_response

        response = galaxy_ng.app.metrics_collection.common_data.api_status()

        self.assertEqual(response, mocked_api_status)

        mock_request.assert_called_with("GET",
                                        'https://example.com/api-test/xxx/pulp/api/v3/status/')
        json_response.assert_called_once()
