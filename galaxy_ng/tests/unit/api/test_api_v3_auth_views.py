import base64

from django.test import override_settings
from django.urls import reverse

from rest_framework import status as http_code
from rest_framework.authtoken import models as token_models
from rest_framework.response import Response
from rest_framework.test import APIClient, APITestCase

from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import auth as auth_models

from .base import get_current_ui_url


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestTokenViewStandalone(APITestCase):
    def setUp(self):
        super().setUp()
        self.token_url = reverse("galaxy:api:v3:auth-token")
        self.me_url = get_current_ui_url("me")

        self.user = auth_models.User.objects.create_user(username="test", password="test-secret")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _issue_token(self):
        response: Response = self.client.post(self.token_url)
        self.assertEqual(response.status_code, http_code.HTTP_200_OK)
        self.assertTrue("token" in response.data)

        return response.data["token"]

    def test_issue_token(self):
        response: Response = self.client.post(self.token_url)
        self.assertEqual(response.status_code, http_code.HTTP_200_OK)
        self.assertTrue("token" in response.data)
        self.assertEqual(response.data["token"], self._get_token(self.user).key)

    def test_issue_token_basic_auth(self):
        client = APIClient()
        http_authorization = "Basic {}".format(base64.b64encode(b"test:test-secret").decode())
        client.credentials(HTTP_AUTHORIZATION=http_authorization)
        response: Response = client.post(self.token_url)
        self.assertEqual(response.status_code, http_code.HTTP_200_OK)
        self.assertTrue("token" in response.data)

    def test_refresh_token(self):
        token_1 = self._issue_token()
        self.assertTrue(self._token_exists(self.user, token_1))

        token_2 = self._issue_token()

        self.assertNotEqual(token_1, token_2)

        self.assertFalse(self._token_exists(self.user, token_1))
        self.assertTrue(self._token_exists(self.user, token_2))

    def test_token_auth(self):
        token = token_models.Token.objects.create(user=self.user)

        new_client = APIClient()
        new_client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response: Response = new_client.get(self.me_url)
        self.assertEqual(response.status_code, http_code.HTTP_200_OK)

    def test_token_auth_missing_token(self):
        new_client = APIClient()

        response: Response = new_client.get(self.me_url)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data,
            {
                "errors": [
                    {
                        "code": "not_authenticated",
                        "status": "403",
                        "title": "Authentication credentials were not provided.",
                    }
                ]
            },
        )

    def test_token_auth_invalid_token(self):
        new_client = APIClient()
        new_client.credentials(HTTP_AUTHORIZATION="Token c451947e96372bc215c1a9e9e9d01eca910cd144")

        response: Response = new_client.get(self.me_url)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data,
            {
                "errors": [
                    {
                        "detail": "Invalid token.",
                        "code": "authentication_failed",
                        "status": "403",
                        "title": "Incorrect authentication credentials.",
                    }
                ]
            },
        )

    def test_revoke_token(self):
        token_models.Token.objects.create(user=self.user)

        response: Response = self.client.delete(self.token_url)
        self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT)

        token_exists = token_models.Token.objects.filter(user=self.user).exists()
        self.assertFalse(token_exists)

    @staticmethod
    def _get_token(user):
        return token_models.Token.objects.get(user=user)

    @staticmethod
    def _token_exists(user, token):
        return token_models.Token.objects.filter(user=user, key=token).exists()
