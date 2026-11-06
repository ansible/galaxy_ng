from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from pulpcore.app.views.status import LivezView, StatusView

from galaxy_ng.app.api.base import GALAXY_AUTHENTICATION_CLASSES


def status_response(*args, **kwargs):
    return Response({
        "database_connection": {"connected": True},
        "redis_connection": {"connected": True},
        "versions": [{"component": "pulp", "version": "3.0"}],
    })


class TestPulpcoreStatusAuthentication(SimpleTestCase):
    @patch.object(
        StatusView,
        "get",
        side_effect=status_response,
    )
    def test_anonymous_status_is_limited_to_health(self, mock_get):
        request = APIRequestFactory().get('/pulp/api/v3/status/')
        request.META['REMOTE_ADDR'] = '10.0.0.1'

        response = StatusView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            "database_connection": {"connected": True},
            "redis_connection": {"connected": True},
        })
        self.assertEqual(response["Cache-Control"], "private")
        self.assertIn("Authorization", response["Vary"])
        self.assertIn("Cookie", response["Vary"])
        self.assertEqual(mock_get.call_count, 1)

    @patch.object(
        StatusView,
        "get",
        side_effect=status_response,
    )
    def test_authenticated_status_keeps_full_response(self, mock_get):
        request = APIRequestFactory().get('/pulp/api/v3/status/')
        request.META['REMOTE_ADDR'] = '10.0.0.1'
        force_authenticate(request, user=get_user_model()(username='test'))

        response = StatusView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn('versions', response.data)
        self.assertEqual(StatusView.authentication_classes, GALAXY_AUTHENTICATION_CLASSES)
        mock_get.assert_called_once()

    def test_anonymous_options_keeps_metadata(self):
        request = APIRequestFactory().options('/pulp/api/v3/status/')

        response = StatusView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(set(response.data), {
            "database_connection",
            "redis_connection",
        })

    def test_livez_remains_public(self):
        request = APIRequestFactory().get('/pulp/api/v3/livez/')

        response = LivezView.as_view()(request)

        self.assertEqual(response.status_code, 200)
