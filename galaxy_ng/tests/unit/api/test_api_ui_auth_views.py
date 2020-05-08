from django.test import override_settings
from django.urls import reverse

from rest_framework import status as http_code
from rest_framework.authtoken import models as token_models
from rest_framework.response import Response
from rest_framework.test import APIClient, APITestCase

from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import auth as auth_models

import logging

LOG = logging.getLogger(__name__)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestLoginViewsStandalone(APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.login_url = reverse("galaxy:api:ui:auth-login")
        self.logout_url = reverse("galaxy:api:ui:auth-logout")
        self.me_url = reverse("galaxy:api:ui:me")

        self.users = [
            auth_models.User.objects.create_user(username="test1", password="test1-secret"),
            auth_models.User.objects.create_user(username="test2", password="test2-secret"),
        ]

    def _test_login_user(self, username, password):
        response: Response = self.client.post(
            self.login_url, data={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT)
        self.assertTrue("csrftoken" in response.cookies)
        self.assertTrue("sessionid" in response.cookies)

        response: Response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, http_code.HTTP_200_OK)
        self.assertEqual(response.data["username"], username)

    def test_login(self):
        self._test_login_user("test1", "test1-secret")
        self._test_login_user("test2", "test2-secret")

    def test_login_invalid_password(self):
        response: Response = self.client.post(
            self.login_url, data={"username": "test1", "password": "invalid",}
        )
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        response: Response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_login_wrong_password(self):
        response: Response = self.client.post(
            self.login_url, data={"username": "test2", "password": "test1-secret",}
        )
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def _test_login_validation_error(
        self, data, expected_code, expected_detail, expected_parameter
    ):
        response: Response = self.client.post(self.login_url, data=data)

        self.assertEqual(response.status_code, http_code.HTTP_400_BAD_REQUEST)
        expected_response_data = {
            "errors": [
                {
                    "status": "400",
                    "code": expected_code,
                    "title": "Invalid input.",
                    "detail": expected_detail,
                    "source": {"parameter": expected_parameter},
                }
            ]
        }
        self.assertDictEqual(response.data, expected_response_data)

    def test_login_no_username(self):
        data = {"password": "test1-secret"}
        self._test_login_validation_error(
            data,
            expected_code="required",
            expected_detail="This field is required.",
            expected_parameter="username",
        )

    def test_login_no_password(self):
        data = {"username": "test1"}
        self._test_login_validation_error(
            data,
            expected_code="required",
            expected_detail="This field is required.",
            expected_parameter="password",
        )

    def test_login_empty_username(self):
        data = {"username": "", "password": "test1-secret"}
        self._test_login_validation_error(
            data,
            expected_code="blank",
            expected_detail="This field may not be blank.",
            expected_parameter="username",
        )

    def test_login_empty_password(self):
        data = {"username": "test1", "password": ""}
        self._test_login_validation_error(
            data,
            expected_code="blank",
            expected_detail="This field may not be blank.",
            expected_parameter="password",
        )

    def test_logout(self):
        response: Response = self.client.post(
            self.login_url, data={"username": "test1", "password": "test1-secret",}
        )
        self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT)

        response: Response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT)

        response: Response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestTokenViewStandalone(APITestCase):
    def setUp(self):
        super().setUp()
        self.token_url = reverse("galaxy:api:ui:auth-token")
        self.me_url = reverse("galaxy:api:ui:me")

        self.user = auth_models.User.objects.create_user(username="test", password="test-secret")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _issue_token(self):
        response: Response = self.client.post(self.token_url)
        self.assertEqual(response.status_code, http_code.HTTP_200_OK)
        self.assertTrue("token" in response.data)

        return response.data["token"]

    def _token_exist(self, user, token):
        return token_models.Token.objects.filter(user=user, key=token).exists()

    def test_issue_token(self):
        self._issue_token()

    def test_reissue_token(self):
        token_1 = self._issue_token()
        self.assertTrue(self._token_exist(self.user, token_1))

        token_2 = self._issue_token()

        self.assertNotEqual(token_1, token_2)

        self.assertFalse(self._token_exist(self.user, token_1))
        self.assertTrue(self._token_exist(self.user, token_2))

    def test_token_auth(self):
        token = token_models.Token.objects.create(user=self.user)

        new_client = APIClient()

        response: Response = new_client.get(self.me_url)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        new_client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response: Response = new_client.get(self.me_url)
        self.assertEqual(response.status_code, http_code.HTTP_200_OK)

    def test_get_token(self):
        token = token_models.Token.objects.create(user=self.user)

        response: Response = self.client.get(self.token_url)
        self.assertEqual(response.status_code, http_code.HTTP_200_OK)
        self.assertTrue("token" in response.data)
        self.assertEqual(response.data["token"], token.key)

    def test_revoke_token(self):
        token = token_models.Token.objects.create(user=self.user)

        response: Response = self.client.delete(self.token_url)
        self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT)

        token_exists = token_models.Token.objects.filter(user=self.user).exists()
        self.assertFalse(token_exists)
