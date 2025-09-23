from unittest.mock import Mock, patch
import pytest
from django.test import TestCase

from galaxy_ng.app.utils.rbac import (
    add_username_to_groupname,
    add_user_to_group,
    remove_username_from_groupname,
    remove_user_from_group,
    add_groupname_to_v3_namespace_name,
    add_group_to_v3_namespace,
    remove_group_from_v3_namespace,
    add_user_to_v3_namespace,
    remove_user_from_v3_namespace,
    get_v3_namespace_owners,
    get_owned_v3_namespaces,
)
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models.auth import Group, User


class TestUserGroupManagement(TestCase):

    def setUp(self):
        self.user = Mock(spec=User)
        self.user.username = "testuser"
        self.group = Mock(spec=Group)
        self.group.name = "testgroup"
        self.group.user_set = Mock()

    @patch('galaxy_ng.app.utils.rbac.User.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.Group.objects.filter')
    def test_add_username_to_groupname(self, mock_group_filter, mock_user_filter):
        mock_user_filter.return_value.first.return_value = self.user
        mock_group_filter.return_value.first.return_value = self.group

        add_username_to_groupname("testuser", "testgroup")

        mock_user_filter.assert_called_once_with(username="testuser")
        mock_group_filter.assert_called_once_with(name="testgroup")
        self.group.user_set.add.assert_called_once_with(self.user)

    def test_add_user_to_group(self):
        add_user_to_group(self.user, self.group)
        self.group.user_set.add.assert_called_once_with(self.user)

    @patch('galaxy_ng.app.utils.rbac.User.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.Group.objects.filter')
    def test_remove_username_from_groupname(self, mock_group_filter, mock_user_filter):
        mock_user_filter.return_value.first.return_value = self.user
        mock_group_filter.return_value.first.return_value = self.group

        remove_username_from_groupname("testuser", "testgroup")

        mock_user_filter.assert_called_once_with(username="testuser")
        mock_group_filter.assert_called_once_with(name="testgroup")
        self.group.user_set.remove.assert_called_once_with(self.user)

    def test_remove_user_from_group(self):
        remove_user_from_group(self.user, self.group)
        self.group.user_set.remove.assert_called_once_with(self.user)

    @patch('galaxy_ng.app.utils.rbac.User.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.Group.objects.filter')
    def test_add_username_to_groupname_user_not_found(self, mock_group_filter, mock_user_filter):
        mock_user_filter.return_value.first.return_value = None
        mock_group_filter.return_value.first.return_value = self.group

        add_username_to_groupname("nonexistent", "testgroup")

        mock_user_filter.assert_called_once_with(username="nonexistent")
        mock_group_filter.assert_called_once_with(name="testgroup")
        self.group.user_set.add.assert_called_once_with(None)

    @patch('galaxy_ng.app.utils.rbac.User.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.Group.objects.filter')
    def test_remove_username_from_groupname_user_not_found(
        self, mock_group_filter, mock_user_filter
    ):
        mock_user_filter.return_value.first.return_value = None
        mock_group_filter.return_value.first.return_value = self.group

        remove_username_from_groupname("nonexistent", "testgroup")

        mock_user_filter.assert_called_once_with(username="nonexistent")
        mock_group_filter.assert_called_once_with(name="testgroup")
        self.group.user_set.remove.assert_called_once_with(None)

    @patch('galaxy_ng.app.utils.rbac.User.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.Group.objects.filter')
    def test_remove_username_from_groupname_group_not_found(
        self, mock_group_filter, mock_user_filter
    ):
        mock_user_filter.return_value.first.return_value = self.user
        mock_group_filter.return_value.first.return_value = None

        # This should raise AttributeError as the original code doesn't handle None
        with pytest.raises(AttributeError):
            remove_username_from_groupname("testuser", "nonexistent")

        mock_user_filter.assert_called_once_with(username="testuser")
        mock_group_filter.assert_called_once_with(name="nonexistent")


class TestNamespaceOwnership(TestCase):

    def setUp(self):
        self.user = Mock(spec=User)
        self.group = Mock(spec=Group)
        self.group.name = "testgroup"
        self.group.user_set = Mock()
        self.namespace = Mock(spec=Namespace)
        self.namespace.name = "testnamespace"

    @patch('galaxy_ng.app.utils.rbac.Group.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.Namespace.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.add_group_to_v3_namespace')
    def test_add_groupname_to_v3_namespace_name(self, mock_add_group, mock_namespace_filter,
                                                mock_group_filter):
        mock_group_filter.return_value.first.return_value = self.group
        mock_namespace_filter.return_value.first.return_value = self.namespace

        add_groupname_to_v3_namespace_name("testgroup", "testnamespace")

        mock_group_filter.assert_called_once_with(name="testgroup")
        mock_namespace_filter.assert_called_once_with(name="testnamespace")
        mock_add_group.assert_called_once_with(self.group, self.namespace)

    @patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
    @patch('galaxy_ng.app.utils.rbac.assign_role')
    def test_add_group_to_v3_namespace_new_group(self, mock_assign_role, mock_get_groups):
        mock_get_groups.return_value = []

        add_group_to_v3_namespace(self.group, self.namespace)

        mock_get_groups.assert_called_once_with(
            self.namespace,
            include_model_permissions=False
        )
        mock_assign_role.assert_called_once_with(
            'galaxy.collection_namespace_owner',
            self.group,
            self.namespace
        )

    @patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
    @patch('galaxy_ng.app.utils.rbac.assign_role')
    def test_add_group_to_v3_namespace_existing_group(self, mock_assign_role, mock_get_groups):
        mock_get_groups.return_value = [self.group]

        add_group_to_v3_namespace(self.group, self.namespace)

        mock_get_groups.assert_called_once_with(
            self.namespace,
            include_model_permissions=False
        )
        mock_assign_role.assert_not_called()

    @patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
    @patch('galaxy_ng.app.utils.rbac.remove_role')
    def test_remove_group_from_v3_namespace_existing_group(self, mock_remove_role, mock_get_groups):
        mock_get_groups.return_value = [self.group]

        remove_group_from_v3_namespace(self.group, self.namespace)

        mock_get_groups.assert_called_once_with(
            self.namespace,
            include_model_permissions=False
        )
        mock_remove_role.assert_called_once_with(
            'galaxy.collection_namespace_owner',
            self.group,
            self.namespace
        )

    @patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
    @patch('galaxy_ng.app.utils.rbac.remove_role')
    def test_remove_group_from_v3_namespace_not_existing_group(self, mock_remove_role,
                                                               mock_get_groups):
        mock_get_groups.return_value = []

        remove_group_from_v3_namespace(self.group, self.namespace)

        mock_get_groups.assert_called_once_with(
            self.namespace,
            include_model_permissions=False
        )
        mock_remove_role.assert_not_called()

    @patch('galaxy_ng.app.utils.rbac.assign_role')
    def test_add_user_to_v3_namespace(self, mock_assign_role):
        add_user_to_v3_namespace(self.user, self.namespace)

        mock_assign_role.assert_called_once_with(
            'galaxy.collection_namespace_owner',
            self.user,
            self.namespace
        )

    @patch('galaxy_ng.app.utils.rbac.remove_role')
    def test_remove_user_from_v3_namespace(self, mock_remove_role):
        remove_user_from_v3_namespace(self.user, self.namespace)

        mock_remove_role.assert_called_once_with(
            'galaxy.collection_namespace_owner',
            self.user,
            self.namespace
        )

    @patch('galaxy_ng.app.utils.rbac.Group.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.Namespace.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.add_group_to_v3_namespace')
    def test_add_groupname_to_v3_namespace_name_group_not_found(
        self, mock_add_group, mock_namespace_filter, mock_group_filter
    ):
        mock_group_filter.return_value.first.return_value = None
        mock_namespace_filter.return_value.first.return_value = self.namespace

        add_groupname_to_v3_namespace_name("nonexistent", "testnamespace")

        mock_group_filter.assert_called_once_with(name="nonexistent")
        mock_namespace_filter.assert_called_once_with(name="testnamespace")
        mock_add_group.assert_called_once_with(None, self.namespace)

    @patch('galaxy_ng.app.utils.rbac.Group.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.Namespace.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.add_group_to_v3_namespace')
    def test_add_groupname_to_v3_namespace_name_namespace_not_found(
        self, mock_add_group, mock_namespace_filter, mock_group_filter
    ):
        mock_group_filter.return_value.first.return_value = self.group
        mock_namespace_filter.return_value.first.return_value = None

        add_groupname_to_v3_namespace_name("testgroup", "nonexistent")

        mock_group_filter.assert_called_once_with(name="testgroup")
        mock_namespace_filter.assert_called_once_with(name="nonexistent")
        mock_add_group.assert_called_once_with(self.group, None)


class TestGetNamespaceOwners(TestCase):

    def setUp(self):
        self.namespace = Mock(spec=Namespace)
        self.user1 = Mock(spec=User)
        self.user1.pk = 1
        self.user2 = Mock(spec=User)
        self.user2.pk = 2
        self.user3 = Mock(spec=User)
        self.user3.pk = 3
        self.group = Mock(spec=Group)
        self.group.user_set = Mock()

    @patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
    @patch('galaxy_ng.app.utils.rbac.get_users_with_perms_attached_roles')
    def test_get_v3_namespace_owners(self, mock_get_users, mock_get_groups):
        # Mock group users
        self.group.user_set.all.return_value = [self.user1, self.user2]
        mock_get_groups.return_value = [self.group]

        # Mock direct users
        mock_get_users.return_value = [self.user2, self.user3]  # user2 is duplicate

        result = get_v3_namespace_owners(self.namespace)

        mock_get_groups.assert_called_once_with(
            self.namespace,
            include_model_permissions=False
        )
        mock_get_users.assert_called_once_with(
            self.namespace,
            include_model_permissions=False
        )

        # Should return unique users only
        self.assertEqual(len(result), 3)
        self.assertIn(self.user1, result)
        self.assertIn(self.user2, result)
        self.assertIn(self.user3, result)

    @patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
    @patch('galaxy_ng.app.utils.rbac.get_users_with_perms_attached_roles')
    def test_get_v3_namespace_owners_no_groups(self, mock_get_users, mock_get_groups):
        mock_get_groups.return_value = []
        mock_get_users.return_value = [self.user1]

        result = get_v3_namespace_owners(self.namespace)

        self.assertEqual(len(result), 1)
        self.assertIn(self.user1, result)

    @patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
    @patch('galaxy_ng.app.utils.rbac.get_users_with_perms_attached_roles')
    def test_get_v3_namespace_owners_no_users(self, mock_get_users, mock_get_groups):
        mock_get_groups.return_value = []
        mock_get_users.return_value = []

        result = get_v3_namespace_owners(self.namespace)

        self.assertEqual(len(result), 0)

    @patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
    @patch('galaxy_ng.app.utils.rbac.get_users_with_perms_attached_roles')
    def test_get_v3_namespace_owners_empty_groups(self, mock_get_users, mock_get_groups):
        # Mock empty group
        self.group.user_set.all.return_value = []
        mock_get_groups.return_value = [self.group]
        mock_get_users.return_value = [self.user1]

        result = get_v3_namespace_owners(self.namespace)

        self.assertEqual(len(result), 1)
        self.assertIn(self.user1, result)

    @patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
    @patch('galaxy_ng.app.utils.rbac.get_users_with_perms_attached_roles')
    def test_get_v3_namespace_owners_multiple_groups(self, mock_get_users, mock_get_groups):
        # Create additional mocks for multiple groups
        group2 = Mock(spec=Group)
        group2.user_set = Mock()
        user4 = Mock(spec=User)
        user4.pk = 4

        # Mock group users
        self.group.user_set.all.return_value = [self.user1, self.user2]
        group2.user_set.all.return_value = [self.user3, user4]
        mock_get_groups.return_value = [self.group, group2]

        # Mock direct users
        mock_get_users.return_value = [self.user2]  # duplicate from groups

        result = get_v3_namespace_owners(self.namespace)

        # Should return unique users from all groups plus direct users
        self.assertEqual(len(result), 4)
        self.assertIn(self.user1, result)
        self.assertIn(self.user2, result)
        self.assertIn(self.user3, result)
        self.assertIn(user4, result)


class TestGetOwnedNamespaces(TestCase):

    def setUp(self):
        self.user = Mock(spec=User)
        self.role = Mock()
        self.namespace1 = Mock(spec=Namespace)
        self.namespace2 = Mock(spec=Namespace)

    @patch('galaxy_ng.app.utils.rbac.Role.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.get_objects_for_user')
    @patch('galaxy_ng.app.utils.rbac.Namespace.objects.all')
    def test_get_owned_v3_namespaces(self, mock_namespace_all, mock_get_objects, mock_role_filter):
        # Mock role and permissions
        self.role.permissions.values_list.return_value = ["change_namespace", "view_namespace"]
        mock_role_filter.return_value.first.return_value = self.role

        # Mock namespace queryset
        mock_namespace_queryset = Mock()
        mock_namespace_all.return_value = mock_namespace_queryset

        # Mock owned namespaces
        mock_get_objects.return_value = [self.namespace1, self.namespace2]

        result = get_owned_v3_namespaces(self.user)

        mock_role_filter.assert_called_once_with(name='galaxy.collection_namespace_owner')
        self.role.permissions.values_list.assert_called_once_with("codename", flat=True)
        mock_get_objects.assert_called_once_with(
            self.user,
            ["change_namespace", "view_namespace"],
            mock_namespace_queryset
        )
        self.assertEqual(result, [self.namespace1, self.namespace2])

    @patch('galaxy_ng.app.utils.rbac.Role.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.get_objects_for_user')
    @patch('galaxy_ng.app.utils.rbac.Namespace.objects.all')
    def test_get_owned_v3_namespaces_no_role(
        self, mock_namespace_all, mock_get_objects, mock_role_filter
    ):
        mock_role_filter.return_value.first.return_value = None

        # Mock namespace queryset
        mock_namespace_queryset = Mock()
        mock_namespace_all.return_value = mock_namespace_queryset

        # This should trigger an AttributeError when trying to access permissions on None
        with pytest.raises(AttributeError):
            get_owned_v3_namespaces(self.user)

        mock_role_filter.assert_called_once_with(name='galaxy.collection_namespace_owner')
        mock_get_objects.assert_not_called()

    @patch('galaxy_ng.app.utils.rbac.Role.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.get_objects_for_user')
    @patch('galaxy_ng.app.utils.rbac.Namespace.objects.all')
    def test_get_owned_v3_namespaces_no_namespaces(
        self, mock_namespace_all, mock_get_objects, mock_role_filter
    ):
        # Mock role and permissions
        self.role.permissions.values_list.return_value = ["change_namespace", "view_namespace"]
        mock_role_filter.return_value.first.return_value = self.role

        # Mock namespace queryset
        mock_namespace_queryset = Mock()
        mock_namespace_all.return_value = mock_namespace_queryset

        # Mock no owned namespaces
        mock_get_objects.return_value = []

        result = get_owned_v3_namespaces(self.user)

        self.assertEqual(result, [])

    @patch('galaxy_ng.app.utils.rbac.Role.objects.filter')
    @patch('galaxy_ng.app.utils.rbac.get_objects_for_user')
    @patch('galaxy_ng.app.utils.rbac.Namespace.objects.all')
    def test_get_owned_v3_namespaces_role_with_no_permissions(
        self, mock_namespace_all, mock_get_objects, mock_role_filter
    ):
        # Mock role with no permissions
        self.role.permissions.values_list.return_value = []
        mock_role_filter.return_value.first.return_value = self.role

        # Mock namespace queryset
        mock_namespace_queryset = Mock()
        mock_namespace_all.return_value = mock_namespace_queryset
        mock_get_objects.return_value = []

        result = get_owned_v3_namespaces(self.user)

        mock_role_filter.assert_called_once_with(name='galaxy.collection_namespace_owner')
        self.role.permissions.values_list.assert_called_once_with("codename", flat=True)
        mock_get_objects.assert_called_once_with(
            self.user,
            [],
            mock_namespace_queryset
        )
        self.assertEqual(result, [])
