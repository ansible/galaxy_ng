from unittest.mock import Mock, patch
from django.test import TestCase

from galaxy_ng.app import pipelines


class TestUserRolePipeline(TestCase):

    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_role_no_user(self, mock_settings):
        response = {'roles': ['admin']}
        details = {}

        result = pipelines.user_role(response, details, user=None)

        assert result is None

    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_role_no_roles_in_response(self, mock_settings):
        mock_settings.KEYCLOAK_ROLE_TOKEN_CLAIM = 'roles'
        mock_user = Mock()
        response = {}
        details = {}

        result = pipelines.user_role(response, details, user=mock_user)

        assert result is None
        mock_user.save.assert_not_called()

    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_role_empty_roles_list(self, mock_settings):
        mock_settings.KEYCLOAK_ROLE_TOKEN_CLAIM = 'roles'
        mock_user = Mock()
        response = {'roles': []}
        details = {}

        result = pipelines.user_role(response, details, user=mock_user)

        assert result is None
        mock_user.save.assert_not_called()

    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_role_roles_not_list(self, mock_settings):
        mock_settings.KEYCLOAK_ROLE_TOKEN_CLAIM = 'roles'
        mock_user = Mock()
        response = {'roles': 'admin'}
        details = {}

        result = pipelines.user_role(response, details, user=mock_user)

        assert result is None
        mock_user.save.assert_not_called()

    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_role_with_admin_role(self, mock_settings):
        mock_settings.KEYCLOAK_ROLE_TOKEN_CLAIM = 'roles'
        mock_settings.KEYCLOAK_ADMIN_ROLE = 'hubadmin'
        mock_user = Mock()
        response = {'roles': ['user', 'hubadmin', 'viewer']}
        details = {}

        pipelines.user_role(response, details, user=mock_user)

        assert mock_user.is_staff is True
        assert mock_user.is_admin is True
        assert mock_user.is_superuser is True
        mock_user.save.assert_called_once()

    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_role_without_admin_role(self, mock_settings):
        mock_settings.KEYCLOAK_ROLE_TOKEN_CLAIM = 'roles'
        mock_settings.KEYCLOAK_ADMIN_ROLE = 'hubadmin'
        mock_user = Mock()
        response = {'roles': ['user', 'viewer']}
        details = {}

        pipelines.user_role(response, details, user=mock_user)

        assert mock_user.is_staff is False
        assert mock_user.is_admin is False
        assert mock_user.is_superuser is False
        mock_user.save.assert_called_once()

    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_role_with_single_admin_role(self, mock_settings):
        mock_settings.KEYCLOAK_ROLE_TOKEN_CLAIM = 'roles'
        mock_settings.KEYCLOAK_ADMIN_ROLE = 'admin'
        mock_user = Mock()
        response = {'roles': ['admin']}
        details = {}

        pipelines.user_role(response, details, user=mock_user)

        assert mock_user.is_staff is True
        assert mock_user.is_admin is True
        assert mock_user.is_superuser is True
        mock_user.save.assert_called_once()

    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_role_with_extra_args(self, mock_settings):
        mock_settings.KEYCLOAK_ROLE_TOKEN_CLAIM = 'roles'
        mock_settings.KEYCLOAK_ADMIN_ROLE = 'admin'
        mock_user = Mock()
        response = {'roles': ['admin']}
        details = {}

        pipelines.user_role(response, details, user=mock_user, extra_arg='test', kwarg1='value1')

        assert mock_user.is_staff is True
        assert mock_user.is_admin is True
        assert mock_user.is_superuser is True
        mock_user.save.assert_called_once()


class TestUserGroupPipeline(TestCase):

    @patch('galaxy_ng.app.pipelines.Group')
    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_group_no_user(self, mock_settings, mock_group):
        response = {'groups': ['admin']}
        details = {}

        result = pipelines.user_group(response, details, user=None)

        assert result is None
        mock_group.objects.get_or_create.assert_not_called()

    @patch('galaxy_ng.app.pipelines.Group')
    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_group_groups_not_list(self, mock_settings, mock_group):
        mock_settings.KEYCLOAK_GROUP_TOKEN_CLAIM = 'groups'
        mock_user = Mock()
        response = {'groups': 'admin'}
        details = {}

        result = pipelines.user_group(response, details, user=mock_user)

        assert result is None
        mock_group.objects.get_or_create.assert_not_called()
        mock_user.groups.clear.assert_not_called()

    @patch('galaxy_ng.app.pipelines.Group')
    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_group_with_simple_groups(self, mock_settings, mock_group):
        mock_settings.KEYCLOAK_GROUP_TOKEN_CLAIM = 'groups'
        mock_user = Mock()

        mock_group1 = Mock()
        mock_group2 = Mock()
        mock_group.objects.get_or_create.side_effect = [
            (mock_group1, True),
            (mock_group2, False)
        ]

        response = {'groups': ['admin', 'users']}
        details = {}

        pipelines.user_group(response, details, user=mock_user)

        assert mock_group.objects.get_or_create.call_count == 2
        mock_group.objects.get_or_create.assert_any_call(name='admin')
        mock_group.objects.get_or_create.assert_any_call(name='users')

        mock_user.groups.clear.assert_called_once()
        mock_group1.user_set.add.assert_called_once_with(mock_user)
        mock_group2.user_set.add.assert_called_once_with(mock_user)

    @patch('galaxy_ng.app.pipelines.Group')
    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_group_with_nested_group_paths(self, mock_settings, mock_group):
        mock_settings.KEYCLOAK_GROUP_TOKEN_CLAIM = 'groups'
        mock_user = Mock()

        mock_group1 = Mock()
        mock_group2 = Mock()
        mock_group3 = Mock()
        mock_group.objects.get_or_create.side_effect = [
            (mock_group1, True),
            (mock_group2, False),
            (mock_group3, True)
        ]

        response = {'groups': ['/org/department/admin', '/org/users', 'viewer']}
        details = {}

        pipelines.user_group(response, details, user=mock_user)

        assert mock_group.objects.get_or_create.call_count == 3
        mock_group.objects.get_or_create.assert_any_call(name='admin')
        mock_group.objects.get_or_create.assert_any_call(name='users')
        mock_group.objects.get_or_create.assert_any_call(name='viewer')

        mock_user.groups.clear.assert_called_once()
        mock_group1.user_set.add.assert_called_once_with(mock_user)
        mock_group2.user_set.add.assert_called_once_with(mock_user)
        mock_group3.user_set.add.assert_called_once_with(mock_user)

    @patch('galaxy_ng.app.pipelines.Group')
    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_group_with_empty_group_list(self, mock_settings, mock_group):
        mock_settings.KEYCLOAK_GROUP_TOKEN_CLAIM = 'groups'
        mock_user = Mock()
        response = {'groups': []}
        details = {}

        pipelines.user_group(response, details, user=mock_user)

        mock_group.objects.get_or_create.assert_not_called()
        mock_user.groups.clear.assert_called_once()

    @patch('galaxy_ng.app.pipelines.Group')
    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_group_with_single_group(self, mock_settings, mock_group):
        mock_settings.KEYCLOAK_GROUP_TOKEN_CLAIM = 'groups'
        mock_user = Mock()

        mock_group_obj = Mock()
        mock_group.objects.get_or_create.return_value = (mock_group_obj, True)

        response = {'groups': ['single_group']}
        details = {}

        pipelines.user_group(response, details, user=mock_user)

        mock_group.objects.get_or_create.assert_called_once_with(name='single_group')
        mock_user.groups.clear.assert_called_once()
        mock_group_obj.user_set.add.assert_called_once_with(mock_user)

    @patch('galaxy_ng.app.pipelines.Group')
    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_group_with_deeply_nested_path(self, mock_settings, mock_group):
        mock_settings.KEYCLOAK_GROUP_TOKEN_CLAIM = 'groups'
        mock_user = Mock()

        mock_group_obj = Mock()
        mock_group.objects.get_or_create.return_value = (mock_group_obj, True)

        response = {'groups': ['/level1/level2/level3/level4/final_group']}
        details = {}

        pipelines.user_group(response, details, user=mock_user)

        mock_group.objects.get_or_create.assert_called_once_with(name='final_group')
        mock_user.groups.clear.assert_called_once()
        mock_group_obj.user_set.add.assert_called_once_with(mock_user)

    @patch('galaxy_ng.app.pipelines.Group')
    @patch('galaxy_ng.app.pipelines.settings')
    def test_user_group_with_extra_args(self, mock_settings, mock_group):
        mock_settings.KEYCLOAK_GROUP_TOKEN_CLAIM = 'groups'
        mock_user = Mock()

        mock_group_obj = Mock()
        mock_group.objects.get_or_create.return_value = (mock_group_obj, True)

        response = {'groups': ['test_group']}
        details = {}

        pipelines.user_group(response, details, user=mock_user, extra_arg='test', kwarg1='value1')

        mock_group.objects.get_or_create.assert_called_once_with(name='test_group')
        mock_user.groups.clear.assert_called_once()
        mock_group_obj.user_set.add.assert_called_once_with(mock_user)
