from rest_framework import status
from rest_framework.test import APIClient

from galaxy_ng.app.models import auth as auth_models
from .base import BaseTestCase


class TestApiRootVersionDisclosure(BaseTestCase):
    """Verify that version info is hidden from unauthenticated users"""

    url = "/api/galaxy/"

    VERSION_FIELDS = (
        "server_version",
        "galaxy_ng_version",
        "galaxy_ng_commit",
        "galaxy_importer_version",
        "pulp_core_version",
        "pulp_ansible_version",
        "pulp_container_version",
        "ansible_base_version",
        "ansible_lint_version",
        "dynaconf_version",
        "django_version",
        "aap_version",
    )

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.regular_user = auth_models.User.objects.create(
            username="regular", is_superuser=False
        )

    def test_unauthenticated_gets_only_available_versions(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("available_versions", response.data)
        self.assertIn("v3", response.data["available_versions"])
        self.assertNotIn("pulp-v3", response.data["available_versions"])
        for field in self.VERSION_FIELDS:
            self.assertNotIn(field, response.data)

    def test_authenticated_gets_all_versions(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("available_versions", response.data)
        # aap_version is only present when running behind AAP Gateway
        for field in self.VERSION_FIELDS:
            if field == "aap_version":
                continue
            self.assertIn(field, response.data)

    def test_invalid_auth_does_not_disclose_versions(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token invalid123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        for field in self.VERSION_FIELDS:
            self.assertNotIn(field, response.data)

    def test_unauthenticated_nonexistent_path_no_version_leakage(self):
        response = self.client.get("/api/galaxy/nonexistent-path/")
        content = response.content.decode()
        self.assertNotIn("server_version", content)
        self.assertNotIn("galaxy_ng_version", content)
