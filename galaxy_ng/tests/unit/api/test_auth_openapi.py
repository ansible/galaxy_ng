import logging
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
