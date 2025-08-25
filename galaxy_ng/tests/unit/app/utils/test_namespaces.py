from unittest.mock import Mock
from django.test import TestCase

from galaxy_ng.app.utils.namespaces import (
    generate_v3_namespace_from_attributes,
    map_v3_namespace,
    generate_available_namespace_name,
    validate_namespace_name,
    transform_namespace_name
)


class TestNamespaceUtils(TestCase):

    def test_validate_namespace_name_valid(self):
        """Test valid namespace names"""
        valid_names = [
            'valid',
            'valid_name',
            'valid123',
            'a1b2c3',
            'namespace_with_numbers123',
            'ab',  # minimum length (2 chars)
        ]
        for name in valid_names:
            self.assertTrue(validate_namespace_name(name), f"'{name}' should be valid")

    def test_validate_namespace_name_invalid(self):
        """Test invalid namespace names"""
        invalid_names = [
            '_invalid',  # starts with underscore
            '',  # empty
            'a',  # too short (1 char)
            'Invalid',  # uppercase
            'invalid-name',  # contains dash
            'invalid__double',  # double underscore
            '123invalid',  # starts with number
            'invalid.name',  # contains dot
            'invalid name',  # contains space
            'invalid@name',  # contains special character
        ]
        for name in invalid_names:
            self.assertFalse(validate_namespace_name(name), f"'{name}' should be invalid")

    def test_transform_namespace_name(self):
        """Test namespace name transformation"""
        test_cases = [
            ('Test-Name', 'test_name'),
            ('UPPERCASE', 'uppercase'),
            ('mixed-Case_Name', 'mixed_case_name'),
            ('already_valid', 'already_valid'),
            ('Name123', 'name123'),
            ('Multi-Dash-Name', 'multi_dash_name'),
        ]
        for input_name, expected in test_cases:
            result = transform_namespace_name(input_name)
            self.assertEqual(result, expected)

    def test_map_v3_namespace_normal_cases(self):
        """Test mapping v1 namespaces to v3"""
        test_cases = [
            ('valid_name', 'valid_name'),
            ('Valid-Name', 'valid_name'),
            ('test123', 'test123'),
            ('user-name', 'user_name'),
        ]
        for input_name, expected in test_cases:
            result = map_v3_namespace(input_name)
            self.assertEqual(result, expected)

    def test_map_v3_namespace_with_prefix(self):
        """Test mapping that requires gh_ prefix"""
        test_cases = [
            ('123test', 'gh_123test'),  # starts with number
            ('_test', 'gh_test'),  # starts with underscore
            ('__test', 'gh_test'),  # starts with multiple underscores
            ('ab', 'gh_ab'),  # too short (2 chars)
            ('a', 'gh_a'),  # too short (1 char)
            ('_', 'gh_'),  # just underscore
        ]
        for input_name, expected in test_cases:
            result = map_v3_namespace(input_name)
            self.assertEqual(result, expected)

    def test_map_v3_namespace_removes_invalid_chars(self):
        """Test that invalid characters are removed"""
        test_cases = [
            ('test@name', 'testname'),  # @ removed
            ('test.name!', 'testname'),  # . and ! removed
            ('test name', 'testname'),  # space removed
            ('test#$%name', 'testname'),  # special chars removed
            ('Test-123!@#', 'test_123'),  # mixed case, special chars
        ]
        for input_name, expected in test_cases:
            result = map_v3_namespace(input_name)
            self.assertEqual(result, expected)

    def test_generate_v3_namespace_from_attributes_valid_username(self):
        """Test when username is already valid"""
        valid_usernames = ['validuser', 'user123', 'valid_user']
        for username in valid_usernames:
            result = generate_v3_namespace_from_attributes(username=username)
            self.assertEqual(result, username)

    def test_generate_v3_namespace_from_attributes_transform_username(self):
        """Test when username can be transformed to valid"""
        test_cases = [
            ('Valid-User', 'valid_user'),
            ('TEST-USER', 'test_user'),
            ('User-123', 'user_123'),
        ]
        for username, expected in test_cases:
            result = generate_v3_namespace_from_attributes(username=username)
            self.assertEqual(result, expected)

    def test_generate_v3_namespace_from_attributes_map_username(self):
        """Test when username needs mapping (prefix, etc.)"""
        test_cases = [
            ('123user', 'gh_123user'),
            ('_user', 'gh_user'),
            ('a', 'gh_a'),
        ]
        for username, expected in test_cases:
            result = generate_v3_namespace_from_attributes(username=username)
            self.assertEqual(result, expected)

    def test_generate_available_namespace_name(self):
        """Test generating available namespace name when conflicts exist"""
        mock_namespace_model = Mock()

        # Mock that first few attempts return conflicts
        mock_queryset = Mock()
        mock_namespace_model.objects.filter.return_value = mock_queryset

        # First call (login0) has conflicts, second call (login1) is available
        mock_queryset.count.side_effect = [1, 0]  # conflict, then available

        result = generate_available_namespace_name(
            mock_namespace_model,
            'test-login',
            12345
        )

        self.assertEqual(result, 'test_login1')

        # Verify the right queries were made
        expected_calls = [
            {'name': 'test_login0'},
            {'name': 'test_login1'},
        ]
        for i, expected_kwargs in enumerate(expected_calls):
            self.assertEqual(
                mock_namespace_model.objects.filter.call_args_list[i][1],
                expected_kwargs
            )

    def test_generate_available_namespace_name_immediate_availability(self):
        """Test when first generated name is available"""
        mock_namespace_model = Mock()
        mock_queryset = Mock()
        mock_namespace_model.objects.filter.return_value = mock_queryset
        mock_queryset.count.return_value = 0  # no conflicts

        result = generate_available_namespace_name(
            mock_namespace_model,
            'available-name',
            12345
        )

        self.assertEqual(result, 'available_name0')

    def test_generate_available_namespace_name_multiple_conflicts(self):
        """Test when multiple conflicts exist before finding available name"""
        mock_namespace_model = Mock()
        mock_queryset = Mock()
        mock_namespace_model.objects.filter.return_value = mock_queryset

        # First 3 attempts have conflicts, 4th is available
        mock_queryset.count.side_effect = [1, 1, 1, 0]

        result = generate_available_namespace_name(
            mock_namespace_model,
            'popular-name',
            12345
        )

        self.assertEqual(result, 'popular_name3')
        self.assertEqual(mock_queryset.count.call_count, 4)
