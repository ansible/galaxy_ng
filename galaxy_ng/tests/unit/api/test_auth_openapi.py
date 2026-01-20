import logging
from unittest.mock import patch
import json
# from rest_framework import status
from django.urls import reverse
# from pulp_ansible.app.models import CollectionRemote
from .base import BaseTestCase

from rest_framework import status as http_code

from rest_framework.test import APIClient
from django.conf import settings


log = logging.getLogger(__name__)


class TestOpenAPISpecAuthentication(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.basic_user = self._create_user("basic_user")

    def build_openapi_urls(self):
        pulp_api = "/api/galaxy/pulp/api/v3"
        return [
            # galaxy_ng endpoints
            reverse('swagger-ui'),
            reverse('schema-redoc'),
            reverse('schema-yaml'),
            reverse('schema'),

            # pulp endpoints
            f"{pulp_api}/docs/api.json",
            f"{pulp_api}/docs/api.yaml",
            f"{pulp_api}/docs/",
            f"{pulp_api}/swagger/",
        ]

    def _assert_endpoints_access(self, status_code):
        endpoints = self.build_openapi_urls()
        for endpoint in endpoints:
            log.info(endpoint)
            resp = self.client.get(endpoint)
            self.assertEqual(resp.status_code, status_code)

    def test_openapi_require_authentication(self):
        settings.set("GALAXY_API_SPEC_REQUIRE_AUTHENTICATION", True)
        self._assert_endpoints_access(http_code.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.basic_user)
        self._assert_endpoints_access(http_code.HTTP_200_OK)

    def test_openapi_unathenticated_access(self):
        settings.set("GALAXY_API_SPEC_REQUIRE_AUTHENTICATION", False)
        self._assert_endpoints_access(http_code.HTTP_200_OK)

        self.client.force_authenticate(user=self.basic_user)
        self._assert_endpoints_access(http_code.HTTP_200_OK)

    @patch('galaxy_ng.app.views.os.path.exists', return_value=False)
    def test_static_openapi_file_not_found_no_auth_unauthed(self, mock_exists):
        # Scenario: Auth not required, user unauthenticated, file missing
        # Expected: 404 (file not found error)
        settings.set("GALAXY_API_SPEC_REQUIRE_AUTHENTICATION", False)
        resp = self.client.get(reverse('schema'))
        self.assertEqual(resp.status_code, http_code.HTTP_404_NOT_FOUND)

    @patch('galaxy_ng.app.views.json.load', side_effect=json.JSONDecodeError('test', 'doc', 0))
    def test_static_openapi_invalid_json_no_auth_unauthed(self, mock_json_load):
        # Scenario: Auth not required, user unauthenticated, invalid JSON
        # Expected: 500 (JSON decode error)
        settings.set("GALAXY_API_SPEC_REQUIRE_AUTHENTICATION", False)
        resp = self.client.get(reverse('schema'))
        self.assertEqual(resp.status_code, http_code.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch('galaxy_ng.app.views.os.path.exists', return_value=False)
    def test_static_openapi_file_not_found_auth_required_unauthed(self, mock_exists):
        # Scenario: Auth required, user unauthenticated, file missing
        # Expected: 401 (auth error blocks file check)
        settings.set("GALAXY_API_SPEC_REQUIRE_AUTHENTICATION", True)
        resp = self.client.get(reverse('schema'))
        self.assertEqual(resp.status_code, http_code.HTTP_401_UNAUTHORIZED)

    @patch('galaxy_ng.app.views.json.load', side_effect=json.JSONDecodeError('test', 'doc', 0))
    def test_static_openapi_invalid_json_auth_required_unauthed(self, mock_json_load):
        # Scenario: Auth required, user unauthenticated, invalid JSON
        # Expected: 401 (auth error blocks JSON reading)
        settings.set("GALAXY_API_SPEC_REQUIRE_AUTHENTICATION", True)
        resp = self.client.get(reverse('schema'))
        self.assertEqual(resp.status_code, http_code.HTTP_401_UNAUTHORIZED)

    @patch('galaxy_ng.app.views.os.path.exists', return_value=False)
    def test_static_openapi_file_not_found_auth_required_authed(self, mock_exists):
        # Scenario: Auth required, user authenticated, file missing
        # Expected: 404 (gets past auth, hits file not found)
        settings.set("GALAXY_API_SPEC_REQUIRE_AUTHENTICATION", True)
        self.client.force_authenticate(user=self.basic_user)
        resp = self.client.get(reverse('schema'))
        self.assertEqual(resp.status_code, http_code.HTTP_404_NOT_FOUND)

    @patch('galaxy_ng.app.views.json.load', side_effect=json.JSONDecodeError('test', 'doc', 0))
    def test_static_openapi_invalid_json_auth_required_authed(self, mock_json_load):
        # Scenario: Auth required, user authenticated, invalid JSON
        # Expected: 500 (gets past auth, hits JSON decode error)
        settings.set("GALAXY_API_SPEC_REQUIRE_AUTHENTICATION", True)
        self.client.force_authenticate(user=self.basic_user)
        resp = self.client.get(reverse('schema'))
        self.assertEqual(resp.status_code, http_code.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch('galaxy_ng.app.views.os.path.exists', return_value=False)
    def test_static_openapi_file_not_found_no_auth_authed(self, mock_exists):
        # Scenario: Auth not required, user authenticated, file missing
        # Expected: 404 (file not found error)
        settings.set("GALAXY_API_SPEC_REQUIRE_AUTHENTICATION", False)
        self.client.force_authenticate(user=self.basic_user)
        resp = self.client.get(reverse('schema'))
        self.assertEqual(resp.status_code, http_code.HTTP_404_NOT_FOUND)

    @patch('galaxy_ng.app.views.json.load', side_effect=json.JSONDecodeError('test', 'doc', 0))
    def test_static_openapi_invalid_json_no_auth_authed(self, mock_json_load):
        # Scenario: Auth not required, user authenticated, invalid JSON
        # Expected: 500 (JSON decode error)
        settings.set("GALAXY_API_SPEC_REQUIRE_AUTHENTICATION", False)
        self.client.force_authenticate(user=self.basic_user)
        resp = self.client.get(reverse('schema'))
        self.assertEqual(resp.status_code, http_code.HTTP_500_INTERNAL_SERVER_ERROR)
