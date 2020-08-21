from django.test import override_settings

from rest_framework import status as http_code
from rest_framework.response import Response
from rest_framework.test import APIClient, APITestCase

from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import auth as auth_models

from .base import get_current_ui_url


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestLoginViewsStandalone(APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.login_url = get_current_ui_url("auth-login")
        self.logout_url = get_current_ui_url("auth-logout")
        self.me_url = get_current_ui_url("me")

        self.users = [
            auth_models.User.objects.create_user(username="test1", password="test1-secret"),
            auth_models.User.objects.create_user(username="test2", password="test2-secret"),
        ]

    def test_login(self):
        self._test_login("test1", "test1-secret")
        self._test_login("test2", "test2-secret")

    def test_login_csrf_cookie_set_header_missing(self):
        client = APIClient(enforce_csrf_checks=True)

        # Ensure CSRF cookie is set
        response = client.get(self.login_url)
        self.assertTrue("csrftoken" in response.cookies)

        self._test_login_permission_denied(
            data={"username": "test1", "password": "test1-secret"},
            expected_detail="CSRF Failed: CSRF token missing or incorrect.",
            client=client
        )

    def test_login_csrf_cookie_missing(self):
        client = APIClient(enforce_csrf_checks=True)
        self._test_login_permission_denied(
            data={"username": "test1", "password": "test1-secret"},
            expected_detail="CSRF Failed: CSRF cookie not set.",
            client=client
        )

    def test_login_invalid_password(self):
        response: Response = self.client.post(
            self.login_url, data={"username": "test1", "password": "invalid", }
        )
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        response: Response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_login_wrong_password(self):
        response: Response = self.client.post(
            self.login_url, data={"username": "test2", "password": "test1-secret", }
        )
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

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
            self.login_url, data={"username": "test1", "password": "test1-secret", }
        )
        self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT)

        response: Response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT)

        response: Response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def _test_login(self, username, password, client=None):
        client = client or self.client
        response: Response = client.post(
            self.login_url, data={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT)
        self.assertTrue("csrftoken" in response.cookies)
        self.assertTrue("sessionid" in response.cookies)

        response: Response = client.get(self.me_url)
        self.assertEqual(response.status_code, http_code.HTTP_200_OK)
        self.assertEqual(response.data["username"], username)

    def _test_login_permission_denied(self, data, expected_detail, client=None):
        client = client or self.client
        response: Response = client.post(self.login_url, data)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, {
            "errors": [
                {
                    "status": "403",
                    "code": "permission_denied",
                    "detail": expected_detail,
                    "title": "You do not have permission to perform this action.",
                }
            ]
        })

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
