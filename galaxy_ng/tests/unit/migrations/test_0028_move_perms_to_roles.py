from importlib import import_module
from unittest.mock import Mock
from django.test import TestCase

from galaxy_ng.app.models import User
from galaxy_ng.app.models import Group

from pulp_ansible.app.models import Collection

from pulpcore.app.models.role import GroupRole
from pulpcore.app.models.role import UserRole
from pulpcore.app.models.role import Role

from django.contrib.auth.models import Permission
from guardian.models import GroupObjectPermission
from guardian.models import UserObjectPermission
from guardian.shortcuts import assign_perm as guardian_assign_perm


permission_names = [
    'ansible.delete_collection',
    'ansible.modify_ansible_repo_content',
    'container.add_containernamespace',
    'container.change_containernamespace',
    'container.delete_containerrepository',
    'container.namespace_change_containerdistribution',
    'container.namespace_modify_content_containerpushrepository',
    'container.namespace_push_containerdistribution',
    'galaxy.add_group',
    'galaxy.add_namespace',
    'galaxy.add_user galaxy.change_user',
    'galaxy.change_namespace',
    'galaxy.delete_namespace',
    'galaxy.upload_to_namespace',
    'galaxy.view_group galaxy.view_user'
    'galaxy.view_group',
    'galaxy.view_namespace',
    'galaxy.view_synclist',
    'galaxy.view_user',
]


def get_model(a,b):
    print(f'GET_MODEL: {a} {b}')

    if a == 'auth':
        if b == 'Permission':
            return Permission
    if a == 'galaxy':
        if b == 'Group':
            return Group
    if a == 'core':
        if b == 'GroupRole':
            return GroupRole
        if b == 'UserRole':
            return UserRole
        if b == 'Role':
            return Role
    if a == 'guardian':
        if b == 'UserObjectPermission':
            return UserObjectPermission
        if b == 'GroupObjectPermission':
            return GroupObjectPermission

    return None


# https://gist.githubusercontent.com/bmclaughlin/3a9d61d7310a285dd00627bfdff4ee69/raw/508386973223d3d2615a9ba63ee07e57dfae55c2/resetdb.sh
class TestMigratingPermissionsToRoles(TestCase):

    def setUp(self):

        print('')

        # map out the permissions
        self.permissions = {}
        for perm_name in permission_names:
            app_label = perm_name.split('.')[0]
            codename = perm_name.split('.')[1]
            this_perm = Permission.objects.filter(
                content_type__app_label=app_label,
                codename=codename
            ).first()
            self.permissions[(app_label, codename)] = this_perm

        # make groups
        self.group_names = []
        self.groups = {}
        for x in range(2, 11):
            if x != 2:
                continue
            group_name = f'test_group_{x}'
            self.group_names.append(group_name)
            self.groups[group_name] = Group.objects.create(name=group_name)

        # make users
        self.user_names = []
        self.users = {}
        for x in range(2, 11):
            if x != 2:
                continue
            user_name =f'test_user_{x}'
            self.user_names.append(user_name)
            self.users[user_name] = User.objects.create(username=user_name)

    def tearDown(self):
        for x in GroupRole.objects.all():
            if x.group.name in self.group_names:
                x.delete()
        for k,v in self.groups.items():
            v.delete()
        for k,v in self.users.items():
            v.delete()

    def test_model_permissions_move_to_custom_role(self):

        apps_mock = Mock()
        apps_mock.get_model = get_model

        # Add permissions directly to a group
        for x in [('ansible', 'delete_collection'), ('galaxy', 'upload_to_namespace')]:
            self.groups['test_group_2'].permissions.add(self.permissions[x])
            self.groups['test_group_2'].save()

        # Run migration
        migration = import_module("galaxy_ng.app.migrations.0028_move_perms_to_roles")
        migration.move_permissions_to_roles(apps_mock, None)

        # All permissions on the group should have been removed
        assert self.groups['test_group_2'].permissions.all().count() == 0

        # A single new grouprole should have been created
        assert GroupRole.objects.filter(group=self.groups['test_group_2']).count() == 1
        gr = GroupRole.objects.filter(group=self.groups['test_group_2']).first()
        assert gr.role.name == 'galaxy.publisher'

        # All of the group's permissions should have been moved to the role
        permissions = [(x.content_type.app_label, x.codename) for x in gr.role.permissions.all()]
        assert len(permissions) == 2
        assert ('ansible', 'delete_collection') in permissions
        assert ('galaxy', 'upload_to_namespace') in permissions

    def test_group_object_permissions(self):

        apps_mock = Mock()
        apps_mock.get_model = get_model

    def test_user_object_permissions(self):

        apps_mock = Mock()
        apps_mock.get_model = get_model

        # Define the testuser
        testuser = self.users['test_user_2']

        # Create a collection and allow the user to delete it
        col,_ = Collection.objects.get_or_create(namespace='foo', name='bar')
        guardian_assign_perm('delete_collection', testuser, col)

        # Run migration
        migration = import_module("galaxy_ng.app.migrations.0028_move_perms_to_roles")
        migration.move_permissions_to_roles(apps_mock, None)

        # Ensure a userrole was created for the user+obj+permission
        assert UserRole.objects.filter(user=testuser).count() == 1

        # Ensure a role was created with the concatenated name
        expected_role_name = 'galaxy.' + testuser.username + '_' + str(col.pulp_id)
        assert Role.objects.filter(name=expected_role_name).count() == 1

        # Ensure the role has only 1 permission
        role = Role.objects.filter(name=expected_role_name).first()
        assert role.permissions.all().count() == 1

        # Ensure the role permission is the right one
        role_perm = role.permissions.first()
        assert role_perm.content_type.app_label == 'ansible'
        assert role_perm.codename == 'delete_collection'
