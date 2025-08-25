from unittest.mock import Mock, patch
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework import exceptions

from galaxy_ng.app.auth.token_auth import ExpiringTokenAuthentication


class TestExpiringTokenAuthentication(TestCase):

    def setUp(self):
        self.auth = ExpiringTokenAuthentication()

    @patch('galaxy_ng.app.auth.token_auth.Token')
    def test_authenticate_credentials_invalid_token(self, mock_token):
        # Create a proper exception class for DoesNotExist
        mock_token.DoesNotExist = Exception
        mock_token.objects.get.side_effect = mock_token.DoesNotExist

        with self.assertRaises(exceptions.AuthenticationFailed) as cm:  # noqa: PT027
            self.auth.authenticate_credentials('invalid_key')

        assert str(cm.exception) == 'Invalid token'
        mock_token.objects.get.assert_called_once_with(key='invalid_key')

    @patch('galaxy_ng.app.auth.token_auth.Token')
    def test_authenticate_credentials_inactive_user(self, mock_token):
        mock_user = Mock()
        mock_user.is_active = False
        mock_token_obj = Mock()
        mock_token_obj.user = mock_user
        mock_token.objects.get.return_value = mock_token_obj

        with self.assertRaises(exceptions.AuthenticationFailed) as cm:  # noqa: PT027
            self.auth.authenticate_credentials('valid_key')

        assert str(cm.exception) == 'User inactive or deleted'

    @patch('galaxy_ng.app.auth.token_auth.Token')
    def test_authenticate_credentials_active_user_no_social_auth(self, mock_token):
        mock_user = Mock()
        mock_user.is_active = True
        del mock_user.social_auth  # User has no social_auth attribute
        mock_token_obj = Mock()
        mock_token_obj.user = mock_user
        mock_token.objects.get.return_value = mock_token_obj

        result = self.auth.authenticate_credentials('valid_key')

        assert result == (mock_user, mock_token_obj)

    @patch('galaxy_ng.app.auth.token_auth.timezone')
    @patch('galaxy_ng.app.auth.token_auth.settings')
    @patch('galaxy_ng.app.auth.token_auth.Token')
    def test_authenticate_credentials_social_auth_user_no_keycloak(
        self, mock_token, mock_settings, mock_timezone
    ):
        from social_django.models import UserSocialAuth

        mock_user = Mock()
        mock_user.is_active = True
        mock_user.social_auth.get.side_effect = UserSocialAuth.DoesNotExist()

        mock_token_obj = Mock()
        mock_token_obj.user = mock_user
        mock_token.objects.get.return_value = mock_token_obj

        result = self.auth.authenticate_credentials('valid_key')

        assert result == (mock_user, mock_token_obj)
        mock_user.social_auth.get.assert_called_once_with(provider="keycloak")

    @patch('galaxy_ng.app.auth.token_auth.timezone')
    @patch('galaxy_ng.app.auth.token_auth.settings')
    @patch('galaxy_ng.app.auth.token_auth.Token')
    def test_authenticate_credentials_keycloak_user_token_not_expired(
        self, mock_token, mock_settings, mock_timezone
    ):
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.social_auth.get.return_value = Mock()  # Keycloak user exists

        now = timezone.now()
        mock_timezone.now.return_value = now
        mock_settings.get.return_value = '1440'  # 24 hours in minutes

        mock_token_obj = Mock()
        mock_token_obj.user = mock_user
        mock_token_obj.created = now - timedelta(minutes=60)  # 1 hour old token
        mock_token.objects.get.return_value = mock_token_obj

        result = self.auth.authenticate_credentials('valid_key')

        assert result == (mock_user, mock_token_obj)

    @patch('galaxy_ng.app.auth.token_auth.timezone')
    @patch('galaxy_ng.app.auth.token_auth.settings')
    @patch('galaxy_ng.app.auth.token_auth.Token')
    def test_authenticate_credentials_keycloak_user_token_expired(
        self, mock_token, mock_settings, mock_timezone
    ):
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.social_auth.get.return_value = Mock()  # Keycloak user exists

        now = timezone.now()
        mock_timezone.now.return_value = now
        mock_settings.get.return_value = '1440'  # 24 hours in minutes

        mock_token_obj = Mock()
        mock_token_obj.user = mock_user
        mock_token_obj.created = now - timedelta(minutes=1500)  # 25 hours old token
        mock_token.objects.get.return_value = mock_token_obj

        with self.assertRaises(exceptions.AuthenticationFailed) as cm:  # noqa: PT027
            self.auth.authenticate_credentials('valid_key')

        assert str(cm.exception) == 'Token has expired'

    @patch('galaxy_ng.app.auth.token_auth.timezone')
    @patch('galaxy_ng.app.auth.token_auth.settings')
    @patch('galaxy_ng.app.auth.token_auth.Token')
    def test_authenticate_credentials_keycloak_user_invalid_expiration_setting(
        self, mock_token, mock_settings, mock_timezone
    ):
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.social_auth.get.return_value = Mock()  # Keycloak user exists

        now = timezone.now()
        mock_timezone.now.return_value = now
        mock_settings.get.return_value = 'invalid_number'  # Non-numeric value

        mock_token_obj = Mock()
        mock_token_obj.user = mock_user
        mock_token_obj.created = now - timedelta(minutes=1500)  # Old token
        mock_token.objects.get.return_value = mock_token_obj

        # Should not raise exception due to ValueError handling
        result = self.auth.authenticate_credentials('valid_key')

        assert result == (mock_user, mock_token_obj)

    @patch('galaxy_ng.app.auth.token_auth.timezone')
    @patch('galaxy_ng.app.auth.token_auth.settings')
    @patch('galaxy_ng.app.auth.token_auth.Token')
    def test_authenticate_credentials_keycloak_user_none_expiration_setting(
        self, mock_token, mock_settings, mock_timezone
    ):
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.social_auth.get.return_value = Mock()  # Keycloak user exists

        now = timezone.now()
        mock_timezone.now.return_value = now
        mock_settings.get.return_value = None  # None value

        mock_token_obj = Mock()
        mock_token_obj.user = mock_user
        mock_token_obj.created = now - timedelta(minutes=1500)  # Old token
        mock_token.objects.get.return_value = mock_token_obj

        # Should not raise exception due to TypeError handling
        result = self.auth.authenticate_credentials('valid_key')

        assert result == (mock_user, mock_token_obj)

    @patch('galaxy_ng.app.auth.token_auth.timezone')
    @patch('galaxy_ng.app.auth.token_auth.settings')
    @patch('galaxy_ng.app.auth.token_auth.Token')
    def test_authenticate_credentials_keycloak_user_zero_expiration(
        self, mock_token, mock_settings, mock_timezone
    ):
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.social_auth.get.return_value = Mock()  # Keycloak user exists

        now = timezone.now()
        mock_timezone.now.return_value = now
        mock_settings.get.return_value = '0'  # Zero minutes expiration

        mock_token_obj = Mock()
        mock_token_obj.user = mock_user
        mock_token_obj.created = now - timedelta(minutes=1)  # 1 minute old token
        mock_token.objects.get.return_value = mock_token_obj

        with self.assertRaises(exceptions.AuthenticationFailed) as cm:  # noqa: PT027
            self.auth.authenticate_credentials('valid_key')

        assert str(cm.exception) == 'Token has expired'

    @patch('galaxy_ng.app.auth.token_auth.timezone')
    @patch('galaxy_ng.app.auth.token_auth.settings')
    @patch('galaxy_ng.app.auth.token_auth.Token')
    def test_authenticate_credentials_keycloak_user_exact_expiration_time(
        self, mock_token, mock_settings, mock_timezone
    ):
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.social_auth.get.return_value = Mock()  # Keycloak user exists

        now = timezone.now()
        mock_timezone.now.return_value = now
        mock_settings.get.return_value = '60'  # 60 minutes expiration

        mock_token_obj = Mock()
        mock_token_obj.user = mock_user
        mock_token_obj.created = now - timedelta(minutes=60)  # Exactly 60 minutes old
        mock_token.objects.get.return_value = mock_token_obj

        # Should not expire (created < now - timedelta, so exactly equal should be valid)
        result = self.auth.authenticate_credentials('valid_key')

        assert result == (mock_user, mock_token_obj)

    @patch('galaxy_ng.app.auth.token_auth.timezone')
    @patch('galaxy_ng.app.auth.token_auth.settings')
    @patch('galaxy_ng.app.auth.token_auth.Token')
    def test_authenticate_credentials_keycloak_user_future_created_time(
        self, mock_token, mock_settings, mock_timezone
    ):
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.social_auth.get.return_value = Mock()  # Keycloak user exists

        now = timezone.now()
        mock_timezone.now.return_value = now
        mock_settings.get.return_value = '60'  # 60 minutes expiration

        mock_token_obj = Mock()
        mock_token_obj.user = mock_user
        mock_token_obj.created = now + timedelta(minutes=10)  # Future creation time
        mock_token.objects.get.return_value = mock_token_obj

        # Should not expire (token created in future)
        result = self.auth.authenticate_credentials('valid_key')

        assert result == (mock_user, mock_token_obj)
