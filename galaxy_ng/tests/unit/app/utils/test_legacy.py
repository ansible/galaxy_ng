from unittest.mock import patch, Mock
from django.test import TestCase
from django.contrib.auth import get_user_model

from galaxy_ng.app.utils.legacy import (
    sanitize_avatar_url,
    process_namespace
)

User = get_user_model()


class TestSanitizeAvatarUrl(TestCase):

    def test_sanitize_avatar_url_valid_http(self):
        url = "http://example.com/avatar.jpg"
        result = sanitize_avatar_url(url)
        assert result == "http://example.com/avatar.jpg"

    def test_sanitize_avatar_url_valid_https(self):
        url = "https://example.com/avatar.jpg"
        result = sanitize_avatar_url(url)
        assert result == "https://example.com/avatar.jpg"

    def test_sanitize_avatar_url_with_junk_text(self):
        url = "some junk text https://example.com/avatar.jpg more junk"
        result = sanitize_avatar_url(url)
        assert result == "https://example.com/avatar.jpg"

    def test_sanitize_avatar_url_multiple_urls(self):
        url = "http://first.com/img.jpg and https://second.com/avatar.png"
        result = sanitize_avatar_url(url)
        assert result == "http://first.com/img.jpg"

    def test_sanitize_avatar_url_no_http(self):
        url = "example.com/avatar.jpg"
        result = sanitize_avatar_url(url)
        assert result is None

    def test_sanitize_avatar_url_empty_string(self):
        url = ""
        result = sanitize_avatar_url(url)
        assert result is None

    def test_sanitize_avatar_url_no_valid_url(self):
        url = "not a url at all"
        result = sanitize_avatar_url(url)
        assert result is None


class TestProcessNamespace(TestCase):

    def setUp(self):
        self.namespace_info = {
            'id': 123,
            'avatar_url': 'https://example.com/avatar.jpg',
            'company': 'Test Company',
            'email': 'test@example.com',
            'description': 'Test description',
            'summary_fields': {
                'owners': [
                    {
                        'username': 'testuser',
                        'github_id': 12345
                    }
                ]
            }
        }

    @patch('galaxy_ng.app.utils.legacy.get_v3_namespace_owners')
    @patch('galaxy_ng.app.utils.legacy.add_user_to_v3_namespace')
    @patch('galaxy_ng.app.utils.legacy.generate_v3_namespace_from_attributes')
    @patch('galaxy_ng.app.utils.legacy.generate_unverified_email')
    @patch('galaxy_ng.app.utils.legacy.User')
    @patch('galaxy_ng.app.utils.legacy.Namespace')
    @patch('galaxy_ng.app.utils.legacy.LegacyNamespace')
    def test_process_namespace_new_legacy_namespace(
        self, mock_legacy_ns, mock_namespace, mock_user,
        mock_gen_email, mock_gen_v3_name, mock_add_user, mock_get_owners
    ):
        # Setup mocks
        mock_legacy_ns_instance = Mock()
        mock_legacy_ns_instance.namespace = None
        mock_legacy_ns.objects.get_or_create.return_value = (mock_legacy_ns_instance, True)

        mock_namespace_instance = Mock()
        mock_namespace_instance.avatar_url = None
        mock_namespace_instance.company = None
        mock_namespace_instance.email = None
        mock_namespace_instance.description = None
        mock_namespace.objects.get_or_create.return_value = (mock_namespace_instance, True)

        mock_gen_v3_name.return_value = 'testuser_12345'
        mock_gen_email.return_value = '12345@GALAXY.GITHUB.UNVERIFIED.COM'

        mock_user_instance = Mock()
        mock_user_instance.email = None
        mock_user.objects.filter.return_value.first.return_value = mock_user_instance
        mock_get_owners.return_value = []

        # Execute
        result = process_namespace('testuser', self.namespace_info)

        # Verify
        assert result == (mock_legacy_ns_instance, mock_namespace_instance)
        mock_legacy_ns.objects.get_or_create.assert_called_once_with(name='testuser')
        mock_gen_v3_name.assert_called_once()
        mock_add_user.assert_called_once()

    @patch('galaxy_ng.app.utils.legacy.get_v3_namespace_owners')
    @patch('galaxy_ng.app.utils.legacy.add_user_to_v3_namespace')
    @patch('galaxy_ng.app.utils.legacy.generate_unverified_email')
    @patch('galaxy_ng.app.utils.legacy.User')
    @patch('galaxy_ng.app.utils.legacy.LegacyNamespace')
    def test_process_namespace_existing_legacy_with_namespace(
        self, mock_legacy_ns, mock_user, mock_gen_email, mock_add_user, mock_get_owners
    ):
        # Setup existing legacy namespace with linked namespace
        mock_namespace_instance = Mock()
        mock_namespace_instance.avatar_url = 'existing.jpg'
        mock_namespace_instance.company = 'Existing Company'
        mock_namespace_instance.email = 'existing@example.com'
        mock_namespace_instance.description = 'Existing description'

        mock_legacy_ns_instance = Mock()
        mock_legacy_ns_instance.namespace = mock_namespace_instance
        mock_legacy_ns.objects.get_or_create.return_value = (mock_legacy_ns_instance, False)

        mock_gen_email.return_value = '12345@GALAXY.GITHUB.UNVERIFIED.COM'
        mock_user_instance = Mock()
        mock_user_instance.email = 'test@example.com'
        mock_user.objects.filter.return_value.first.return_value = mock_user_instance
        mock_get_owners.return_value = [mock_user_instance]

        # Execute
        result = process_namespace('testuser', self.namespace_info)

        # Verify - should not update existing values without force
        assert result == (mock_legacy_ns_instance, mock_namespace_instance)
        mock_namespace_instance.save.assert_not_called()

    @patch('galaxy_ng.app.utils.legacy.get_v3_namespace_owners')
    @patch('galaxy_ng.app.utils.legacy.add_user_to_v3_namespace')
    @patch('galaxy_ng.app.utils.legacy.generate_v3_namespace_from_attributes')
    @patch('galaxy_ng.app.utils.legacy.generate_unverified_email')
    @patch('galaxy_ng.app.utils.legacy.User')
    @patch('galaxy_ng.app.utils.legacy.Namespace')
    @patch('galaxy_ng.app.utils.legacy.LegacyNamespace')
    def test_process_namespace_force_update(
        self, mock_legacy_ns, mock_namespace, mock_user,
        mock_gen_email, mock_gen_v3_name, mock_add_user, mock_get_owners
    ):
        # Setup mocks
        mock_legacy_ns_instance = Mock()
        mock_legacy_ns_instance.namespace = None
        mock_legacy_ns.objects.get_or_create.return_value = (mock_legacy_ns_instance, False)

        mock_namespace_instance = Mock()
        mock_namespace_instance.avatar_url = 'old.jpg'
        mock_namespace_instance.company = 'Old Company'
        mock_namespace_instance.email = 'old@example.com'
        mock_namespace_instance.description = 'Old description'
        mock_namespace.objects.get_or_create.return_value = (mock_namespace_instance, False)

        mock_gen_v3_name.return_value = 'testuser_12345'
        mock_gen_email.return_value = '12345@GALAXY.GITHUB.UNVERIFIED.COM'

        mock_user_instance = Mock()
        mock_user_instance.email = 'test@example.com'
        mock_user.objects.filter.return_value.first.return_value = mock_user_instance
        mock_get_owners.return_value = []

        # Execute with force=True
        process_namespace('testuser', self.namespace_info, force=True)

        # Verify updates were forced
        assert mock_namespace_instance.avatar_url == 'https://example.com/avatar.jpg'
        assert mock_namespace_instance.company == 'Test Company'
        assert mock_namespace_instance.email == 'test@example.com'
        assert mock_namespace_instance.description == 'Test description'
        mock_namespace_instance.save.assert_called()

    @patch('galaxy_ng.app.utils.legacy.get_v3_namespace_owners')
    @patch('galaxy_ng.app.utils.legacy.add_user_to_v3_namespace')
    @patch('galaxy_ng.app.utils.legacy.generate_v3_namespace_from_attributes')
    @patch('galaxy_ng.app.utils.legacy.generate_unverified_email')
    @patch('galaxy_ng.app.utils.legacy.User')
    @patch('galaxy_ng.app.utils.legacy.Namespace')
    @patch('galaxy_ng.app.utils.legacy.LegacyNamespace')
    def test_process_namespace_long_company_truncation(
        self, mock_legacy_ns, mock_namespace, mock_user,
        mock_gen_email, mock_gen_v3_name, mock_add_user, mock_get_owners
    ):
        # Setup namespace info with long company name
        long_company = 'A' * 70  # Longer than 60 characters
        namespace_info = self.namespace_info.copy()
        namespace_info['company'] = long_company

        mock_legacy_ns_instance = Mock()
        mock_legacy_ns_instance.namespace = None
        mock_legacy_ns.objects.get_or_create.return_value = (mock_legacy_ns_instance, False)

        mock_namespace_instance = Mock()
        mock_namespace_instance.avatar_url = None
        mock_namespace_instance.company = None
        mock_namespace_instance.email = None
        mock_namespace_instance.description = None
        mock_namespace.objects.get_or_create.return_value = (mock_namespace_instance, False)

        mock_gen_v3_name.return_value = 'testuser_12345'
        mock_gen_email.return_value = '12345@GALAXY.GITHUB.UNVERIFIED.COM'

        mock_user_instance = Mock()
        mock_user.objects.filter.return_value.first.return_value = mock_user_instance
        mock_get_owners.return_value = []

        # Execute
        process_namespace('testuser', namespace_info)

        # Verify company was truncated to 60 characters
        assert mock_namespace_instance.company == 'A' * 60

    @patch('galaxy_ng.app.utils.legacy.get_v3_namespace_owners')
    @patch('galaxy_ng.app.utils.legacy.add_user_to_v3_namespace')
    @patch('galaxy_ng.app.utils.legacy.generate_v3_namespace_from_attributes')
    @patch('galaxy_ng.app.utils.legacy.generate_unverified_email')
    @patch('galaxy_ng.app.utils.legacy.User')
    @patch('galaxy_ng.app.utils.legacy.Namespace')
    @patch('galaxy_ng.app.utils.legacy.LegacyNamespace')
    def test_process_namespace_owner_without_github_id(
        self, mock_legacy_ns, mock_namespace, mock_user,
        mock_gen_email, mock_gen_v3_name, mock_add_user, mock_get_owners
    ):
        # Setup namespace info with owner without github_id
        namespace_info = self.namespace_info.copy()
        namespace_info['summary_fields']['owners'] = [
            {'username': 'testuser'}  # No github_id
        ]

        mock_legacy_ns_instance = Mock()
        mock_legacy_ns_instance.namespace = None
        mock_legacy_ns.objects.get_or_create.return_value = (mock_legacy_ns_instance, False)

        mock_namespace_instance = Mock()
        mock_namespace_instance.avatar_url = None
        mock_namespace_instance.company = None
        mock_namespace_instance.email = None
        mock_namespace_instance.description = None
        mock_namespace.objects.get_or_create.return_value = (mock_namespace_instance, False)

        mock_gen_v3_name.return_value = 'testuser'

        mock_user_instance = Mock()
        mock_user_instance.email = None
        mock_user.objects.filter.return_value.first.return_value = mock_user_instance
        mock_get_owners.return_value = []

        # Execute
        process_namespace('testuser', namespace_info)

        # Verify generate_v3_namespace_from_attributes called with github_id=-1
        mock_gen_v3_name.assert_called_with(username='testuser', github_id=-1)

    @patch('galaxy_ng.app.utils.legacy.get_v3_namespace_owners')
    @patch('galaxy_ng.app.utils.legacy.add_user_to_v3_namespace')
    @patch('galaxy_ng.app.utils.legacy.generate_v3_namespace_from_attributes')
    @patch('galaxy_ng.app.utils.legacy.generate_unverified_email')
    @patch('galaxy_ng.app.utils.legacy.User')
    @patch('galaxy_ng.app.utils.legacy.Namespace')
    @patch('galaxy_ng.app.utils.legacy.LegacyNamespace')
    def test_process_namespace_create_new_user(
        self, mock_legacy_ns, mock_namespace, mock_user,
        mock_gen_email, mock_gen_v3_name, mock_add_user, mock_get_owners
    ):
        # Setup mocks - no existing user found
        mock_legacy_ns_instance = Mock()
        mock_legacy_ns_instance.namespace = None
        mock_legacy_ns.objects.get_or_create.return_value = (mock_legacy_ns_instance, False)

        mock_namespace_instance = Mock()
        mock_namespace_instance.avatar_url = None
        mock_namespace_instance.company = None
        mock_namespace_instance.email = None
        mock_namespace_instance.description = None
        mock_namespace.objects.get_or_create.return_value = (mock_namespace_instance, False)

        mock_gen_v3_name.return_value = 'testuser_12345'
        mock_gen_email.return_value = '12345@GALAXY.GITHUB.UNVERIFIED.COM'

        # No existing user found
        mock_user.objects.filter.return_value.first.return_value = None

        # New user creation
        mock_new_user = Mock()
        mock_new_user.email = None
        mock_user.objects.get_or_create.return_value = (mock_new_user, True)

        mock_get_owners.return_value = []

        # Execute
        process_namespace('testuser', self.namespace_info)

        # Verify new user was created and email set
        mock_user.objects.get_or_create.assert_called_with(username='testuser')
        assert mock_new_user.email == '12345@GALAXY.GITHUB.UNVERIFIED.COM'
        mock_new_user.save.assert_called()

    @patch('galaxy_ng.app.utils.legacy.sanitize_avatar_url')
    @patch('galaxy_ng.app.utils.legacy.get_v3_namespace_owners')
    @patch('galaxy_ng.app.utils.legacy.add_user_to_v3_namespace')
    @patch('galaxy_ng.app.utils.legacy.generate_v3_namespace_from_attributes')
    @patch('galaxy_ng.app.utils.legacy.User')
    @patch('galaxy_ng.app.utils.legacy.Namespace')
    @patch('galaxy_ng.app.utils.legacy.LegacyNamespace')
    def test_process_namespace_invalid_avatar_url(
        self, mock_legacy_ns, mock_namespace, mock_user,
        mock_gen_v3_name, mock_add_user, mock_get_owners, mock_sanitize
    ):
        # Setup namespace info with only invalid avatar_url and no other fields
        namespace_info = {
            'id': 123,
            'avatar_url': 'invalid_url',
            'summary_fields': {
                'owners': [
                    {
                        'username': 'testuser',
                        'github_id': 12345
                    }
                ]
            }
        }

        # Setup mocks
        mock_legacy_ns_instance = Mock()
        mock_legacy_ns_instance.namespace = None
        mock_legacy_ns.objects.get_or_create.return_value = (mock_legacy_ns_instance, False)

        mock_namespace_instance = Mock()
        mock_namespace_instance.avatar_url = None
        mock_namespace_instance.company = None
        mock_namespace_instance.email = None
        mock_namespace_instance.description = None
        mock_namespace.objects.get_or_create.return_value = (mock_namespace_instance, False)

        mock_gen_v3_name.return_value = 'testuser_12345'
        mock_sanitize.return_value = None  # Invalid URL

        mock_user_instance = Mock()
        mock_user.objects.filter.return_value.first.return_value = mock_user_instance
        mock_get_owners.return_value = []

        # Execute
        process_namespace('testuser', namespace_info)

        # Verify avatar_url was not set due to invalid URL
        assert mock_namespace_instance.avatar_url is None
        mock_namespace_instance.save.assert_not_called()
