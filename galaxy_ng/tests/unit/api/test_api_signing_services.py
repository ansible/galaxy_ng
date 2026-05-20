from rest_framework import status
from rest_framework.test import APIClient

from galaxy_ng.app.models import auth as auth_models
from .base import BaseTestCase


class TestSigningServicesAccessPolicy(BaseTestCase):
    url = "/api/galaxy/pulp/api/v3/signing-services/"
    detail_url = url + "00000000-0000-0000-0000-000000000000/"

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.admin_user = auth_models.User.objects.create(username="admin", is_superuser=True)
        self.regular_user = auth_models.User.objects.create(username="regular", is_superuser=False)

    def _list_as(self, user=None):
        if user:
            self.client.force_authenticate(user=user)
        return self.client.get(self.url)

    def _create_as(self, user):
        self.client.force_authenticate(user=user)
        return self.client.post(
            self.url,
            {"name": "test-signing-service", "script": "/tmp/sign.sh"},
            format="json",
        )

    def _update_as(self, user):
        self.client.force_authenticate(user=user)
        return self.client.patch(self.detail_url, {"name": "updated"}, format="json")

    def test_superuser_can_list(self):
        response = self._list_as(self.admin_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_user_can_list(self):
        response = self._list_as(self.regular_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_user_cannot_list(self):
        response = self._list_as()
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_regular_user_cannot_create(self):
        response = self._create_as(self.regular_user)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_superuser_cannot_create(self):
        response = self._create_as(self.admin_user)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_regular_user_cannot_update(self):
        response = self._update_as(self.regular_user)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_superuser_cannot_update(self):
        response = self._update_as(self.admin_user)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
