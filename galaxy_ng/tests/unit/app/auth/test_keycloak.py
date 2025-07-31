from unittest.mock import Mock, patch
from django.test import TestCase
from rest_framework import status as http_code
from rest_framework import exceptions

from galaxy_ng.app.auth.keycloak import KeycloakBasicAuth


class TestKeycloakBasicAuth(TestCase):

    def setUp(self):
        self.auth = KeycloakBasicAuth()

    @patch('galaxy_ng.app.auth.keycloak.load_strategy')
    @patch('galaxy_ng.app.auth.keycloak.KeycloakOAuth2')
    @patch('galaxy_ng.app.auth.keycloak.requests_post')
    @patch('galaxy_ng.app.auth.keycloak.settings')
    def test_authenticate_credentials_successful_keycloak_auth(
        self, mock_settings, mock_requests_post, mock_keycloak_oauth2, mock_load_strategy
    ):
        # Setup settings
        mock_settings.SOCIAL_AUTH_KEYCLOAK_KEY = 'test_client_id'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_SECRET = 'test_client_secret'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = 'http://keycloak/token'
        mock_settings.GALAXY_VERIFY_KEYCLOAK_SSL_CERTS = True

        # Setup successful response
        mock_response = Mock()
        mock_response.status_code = http_code.HTTP_200_OK
        mock_response.json.return_value = {'access_token': 'test_access_token'}
        mock_requests_post.return_value = mock_response

        # Setup strategy and backend
        mock_strategy = Mock()
        mock_load_strategy.return_value = mock_strategy

        mock_backend = Mock()
        mock_backend.user_data.return_value = {'sub': 'user123', 'preferred_username': 'testuser'}
        mock_keycloak_oauth2.return_value = mock_backend

        mock_user = Mock()
        mock_strategy.authenticate.return_value = mock_user

        mock_request = Mock()

        result = self.auth.authenticate_credentials('testuser', 'testpass', mock_request)

        # Verify the POST request
        mock_requests_post.assert_called_once_with(
            url='http://keycloak/token',
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                'client_id': 'test_client_id',
                'client_secret': 'test_client_secret',
                'grant_type': 'password',
                'scope': 'openid',
                'username': 'testuser',
                'password': 'testpass'
            },
            verify=True
        )

        # Verify strategy loading and backend setup
        mock_load_strategy.assert_called_once_with(mock_request)
        mock_keycloak_oauth2.assert_called_once_with(mock_strategy)
        mock_backend.user_data.assert_called_once_with('test_access_token')
        mock_strategy.authenticate.assert_called_once_with(
            mock_backend, response={'sub': 'user123', 'preferred_username': 'testuser'}
        )

        assert result == (mock_user, None)

    @patch('galaxy_ng.app.auth.keycloak.load_strategy')
    @patch('galaxy_ng.app.auth.keycloak.KeycloakOAuth2')
    @patch('galaxy_ng.app.auth.keycloak.requests_post')
    @patch('galaxy_ng.app.auth.keycloak.settings')
    def test_authenticate_credentials_keycloak_auth_no_user(
        self, mock_settings, mock_requests_post, mock_keycloak_oauth2, mock_load_strategy
    ):
        # Setup settings
        mock_settings.SOCIAL_AUTH_KEYCLOAK_KEY = 'test_client_id'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_SECRET = 'test_client_secret'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = 'http://keycloak/token'
        mock_settings.GALAXY_VERIFY_KEYCLOAK_SSL_CERTS = True

        # Setup successful response
        mock_response = Mock()
        mock_response.status_code = http_code.HTTP_200_OK
        mock_response.json.return_value = {'access_token': 'test_access_token'}
        mock_requests_post.return_value = mock_response

        # Setup strategy and backend
        mock_strategy = Mock()
        mock_load_strategy.return_value = mock_strategy

        mock_backend = Mock()
        mock_backend.user_data.return_value = {'sub': 'user123', 'preferred_username': 'testuser'}
        mock_keycloak_oauth2.return_value = mock_backend

        # Strategy authenticate returns None (no user found)
        mock_strategy.authenticate.return_value = None

        mock_request = Mock()

        with self.assertRaises(exceptions.AuthenticationFailed) as cm:  # noqa: PT027
            self.auth.authenticate_credentials('testuser', 'testpass', mock_request)

        assert str(cm.exception) == 'Authentication failed.'

    @patch('galaxy_ng.app.auth.keycloak.requests_post')
    @patch('galaxy_ng.app.auth.keycloak.settings')
    def test_authenticate_credentials_keycloak_auth_failed(self, mock_settings, mock_requests_post):
        # Setup settings
        mock_settings.SOCIAL_AUTH_KEYCLOAK_KEY = 'test_client_id'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_SECRET = 'test_client_secret'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = 'http://keycloak/token'
        mock_settings.GALAXY_VERIFY_KEYCLOAK_SSL_CERTS = True

        # Setup failed response
        mock_response = Mock()
        mock_response.status_code = http_code.HTTP_401_UNAUTHORIZED
        mock_requests_post.return_value = mock_response

        mock_request = Mock()

        # Should fall back to parent authentication
        with patch.object(KeycloakBasicAuth.__bases__[0], 'authenticate_credentials') as mock_super:
            mock_super.return_value = ('parent_result', 'parent_token')

            result = self.auth.authenticate_credentials('testuser', 'wrongpass', mock_request)

            mock_super.assert_called_once_with('testuser', 'wrongpass', mock_request)
            assert result == ('parent_result', 'parent_token')

    @patch('galaxy_ng.app.auth.keycloak.requests_post')
    @patch('galaxy_ng.app.auth.keycloak.settings')
    def test_authenticate_credentials_ssl_verification_disabled(
        self, mock_settings, mock_requests_post
    ):
        # Setup settings with SSL verification disabled
        mock_settings.SOCIAL_AUTH_KEYCLOAK_KEY = 'test_client_id'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_SECRET = 'test_client_secret'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = 'http://keycloak/token'
        mock_settings.GALAXY_VERIFY_KEYCLOAK_SSL_CERTS = False

        # Setup failed response to check call arguments
        mock_response = Mock()
        mock_response.status_code = http_code.HTTP_401_UNAUTHORIZED
        mock_requests_post.return_value = mock_response

        mock_request = Mock()

        with patch.object(KeycloakBasicAuth.__bases__[0], 'authenticate_credentials') as mock_super:
            mock_super.return_value = ('parent_result', 'parent_token')

            self.auth.authenticate_credentials('testuser', 'testpass', mock_request)

            # Verify SSL verification is disabled
            mock_requests_post.assert_called_once_with(
                url='http://keycloak/token',
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    'client_id': 'test_client_id',
                    'client_secret': 'test_client_secret',
                    'grant_type': 'password',
                    'scope': 'openid',
                    'username': 'testuser',
                    'password': 'testpass'
                },
                verify=False
            )

    @patch('galaxy_ng.app.auth.keycloak.requests_post')
    @patch('galaxy_ng.app.auth.keycloak.settings')
    def test_authenticate_credentials_no_request_object(
        self, mock_settings, mock_requests_post
    ):
        # Setup settings
        mock_settings.SOCIAL_AUTH_KEYCLOAK_KEY = 'test_client_id'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_SECRET = 'test_client_secret'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = 'http://keycloak/token'
        mock_settings.GALAXY_VERIFY_KEYCLOAK_SSL_CERTS = True

        # Setup failed response
        mock_response = Mock()
        mock_response.status_code = http_code.HTTP_401_UNAUTHORIZED
        mock_requests_post.return_value = mock_response

        # Should fall back to parent authentication with None request
        with patch.object(KeycloakBasicAuth.__bases__[0], 'authenticate_credentials') as mock_super:
            mock_super.return_value = ('parent_result', 'parent_token')

            result = self.auth.authenticate_credentials('testuser', 'testpass', None)

            mock_super.assert_called_once_with('testuser', 'testpass', None)
            assert result == ('parent_result', 'parent_token')

    @patch('galaxy_ng.app.auth.keycloak.load_strategy')
    @patch('galaxy_ng.app.auth.keycloak.KeycloakOAuth2')
    @patch('galaxy_ng.app.auth.keycloak.requests_post')
    @patch('galaxy_ng.app.auth.keycloak.settings')
    def test_authenticate_credentials_payload_construction(
        self, mock_settings, mock_requests_post, mock_keycloak_oauth2, mock_load_strategy
    ):
        # Setup settings
        mock_settings.SOCIAL_AUTH_KEYCLOAK_KEY = 'my_client'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_SECRET = 'my_secret'
        mock_settings.SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = 'https://sso.example.com/token'
        mock_settings.GALAXY_VERIFY_KEYCLOAK_SSL_CERTS = True

        # Setup failed response to check payload
        mock_response = Mock()
        mock_response.status_code = http_code.HTTP_400_BAD_REQUEST
        mock_requests_post.return_value = mock_response

        with patch.object(KeycloakBasicAuth.__bases__[0], 'authenticate_credentials') as mock_super:
            mock_super.return_value = ('parent_result', 'parent_token')

            self.auth.authenticate_credentials('user@domain.com', 'complex$password', None)

            # Verify exact payload structure
            expected_payload = {
                'client_id': 'my_client',
                'client_secret': 'my_secret',
                'grant_type': 'password',
                'scope': 'openid',
                'username': 'user@domain.com',
                'password': 'complex$password'
            }

            mock_requests_post.assert_called_once_with(
                url='https://sso.example.com/token',
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=expected_payload,
                verify=True
            )
