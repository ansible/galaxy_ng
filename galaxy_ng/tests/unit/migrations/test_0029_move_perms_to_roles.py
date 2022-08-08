import importlib

from unittest.case import skipIf

from django.test import TestCase
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission

from galaxy_ng.app.models import User, Group, Namespace
from pulp_container.app.models import ContainerNamespace
from pulpcore.app.models.role import GroupRole, UserRole, Role
from pulpcore.plugin.util import assign_role


# Note, this copied from galaxy_ng.app.access_control.statements.roles instead of
# imported because the roles may change in the future, but the migrations don't
LOCKED_ROLES = {
    "galaxy.content_admin": {
        "permissions": [
            "galaxy.add_namespace",
            "galaxy.change_namespace",
            "galaxy.delete_namespace",
            "galaxy.upload_to_namespace",
            "ansible.delete_collection",
            "ansible.change_collectionremote",
            "ansible.view_collectionremote",
            "ansible.modify_ansible_repo_content",
            "container.delete_containerrepository",
            "container.namespace_change_containerdistribution",
            "container.namespace_modify_content_containerpushrepository",
            "container.namespace_push_containerdistribution",
            "container.add_containernamespace",
            "container.change_containernamespace",
            # "container.namespace_add_containerdistribution",
            "galaxy.add_containerregistryremote",
            "galaxy.change_containerregistryremote",
            "galaxy.delete_containerregistryremote",
        ],
        "description": "Manage all content types."
    },

    # COLLECTIONS
    "galaxy.collection_admin": {
        "permissions": [
            "galaxy.add_namespace",
            "galaxy.change_namespace",
            "galaxy.delete_namespace",
            "galaxy.upload_to_namespace",
            "ansible.delete_collection",
            "ansible.change_collectionremote",
            "ansible.view_collectionremote",
            "ansible.modify_ansible_repo_content",
        ],
        "description": (
            "Create, delete and change collection namespaces. "
            "Upload and delete collections. Sync collections from remotes. "
            "Approve and reject collections.")
    },
    "galaxy.collection_publisher": {
        "permissions": [
            "galaxy.add_namespace",
            "galaxy.change_namespace",
            "galaxy.upload_to_namespace",
        ],
        "description": "Upload and modify collections."
    },
    "galaxy.collection_curator": {
        "permissions": [
            "ansible.change_collectionremote",
            "ansible.view_collectionremote",
            "ansible.modify_ansible_repo_content",
        ],
        "description": "Approve, reject and sync collections from remotes.",
    },
    "galaxy.collection_namespace_owner": {
        "permissions": [
            "galaxy.change_namespace",
            "galaxy.upload_to_namespace",
        ],
        "description": "Change and upload collections to namespaces."
    },

    # EXECUTION ENVIRONMENTS
    "galaxy.execution_environment_admin": {
        "permissions": [
            "container.delete_containerrepository",
            "container.namespace_change_containerdistribution",
            "container.namespace_modify_content_containerpushrepository",
            "container.namespace_push_containerdistribution",
            "container.add_containernamespace",
            "container.change_containernamespace",
            # "container.namespace_add_containerdistribution",
            "galaxy.add_containerregistryremote",
            "galaxy.change_containerregistryremote",
            "galaxy.delete_containerregistryremote",
        ],
        "description": (
            "Push, delete, and change execution environments. "
            "Create, delete and change remote registries.")
    },
    "galaxy.execution_environment_publisher": {
        "permissions": [
            "container.namespace_change_containerdistribution",
            "container.namespace_modify_content_containerpushrepository",
            "container.namespace_push_containerdistribution",
            "container.add_containernamespace",
            "container.change_containernamespace",
            # "container.namespace_add_containerdistribution",
        ],
        "description": "Push, and change execution environments."
    },
    "galaxy.execution_environment_namespace_owner": {
        "permissions": [
            "container.change_containernamespace",
            "container.namespace_push_containerdistribution",
            "container.namespace_change_containerdistribution",
            "container.namespace_modify_content_containerpushrepository",
            # "container.namespace_add_containerdistribution",
        ],
        "description": (
            "Create and update execution environments under existing "
            "container namespaces.")
    },
    "galaxy.execution_environment_collaborator": {
        "permissions": [
            "container.namespace_push_containerdistribution",
            "container.namespace_change_containerdistribution",
            "container.namespace_modify_content_containerpushrepository",
        ],
        "description": "Change existing execution environments."
    },

    # ADMIN STUFF
    "galaxy.group_admin": {
        "permissions": [
            "galaxy.view_group",
            "galaxy.delete_group",
            "galaxy.add_group",
            "galaxy.change_group",
        ],
        "description": "View, add, remove and change groups."
    },
    "galaxy.user_admin": {
        "permissions": [
            "galaxy.view_user",
            "galaxy.delete_user",
            "galaxy.add_user",
            "galaxy.change_user",
        ],
        "description": "View, add, remove and change users."
    },
    "galaxy.synclist_owner": {
        "permissions": [
            "galaxy.add_synclist",
            "galaxy.change_synclist",
            "galaxy.delete_synclist",
            "galaxy.view_synclist",
        ],
        "description": "View, add, remove and change synclists."
    },
    "galaxy.task_admin": {
        "permissions": [
            "core.change_task",
            "core.delete_task",
            "core.view_task"
        ],
        "description": "View, and cancel any task."
    },
}


def is_guardian_installed():
    return importlib.util.find_spec("guardian") is not None


class TestMigratingPermissionsToRoles(TestCase):
    _assign_perm = None

    def _get_permission(self, permission_name):
        app_label = permission_name.split('.')[0]
        codename = permission_name.split('.')[1]
        return Permission.objects.get(
            content_type__app_label=app_label,
            codename=codename
        )
    
    def _run_migrations(self):
        migration = importlib.import_module("galaxy_ng.app.migrations.0029_move_perms_to_roles")
        migration.migrate_group_permissions_to_roles(apps, None)
        migration.migrate_user_permissions_to_roles(apps, None)
        migration.edit_guardian_tables(apps, None)
        migration.clear_model_permissions(apps, None)


    def _create_user_and_group_with_permissions(self, name, permissions, obj=None):
        user = User.objects.create(username=f"user_{name}")
        group = Group.objects.create(name=f"group_{name}")
        group.user_set.add(user)

        if obj:
            for perm in permissions:
                self._get_assign_perm(self._get_permission(perm), group, obj)
        else:
            for perm in permissions:
                group.permissions.add(self._get_permission(perm))
        group.save()

        return (user, group)

    def _has_role(self, group, role, obj=None):
        role_obj = Role.objects.get(name=role)

        if obj:
            c_type = ContentType.objects.get_for_model(obj)
            return GroupRole.objects.filter(
                group=group,
                role=role_obj,
                content_type=c_type,
                object_id=obj.pk).exists()
        else:
            return GroupRole.objects.filter(
                group=group,
                role=role_obj).exists()

    @property
    def _get_assign_perm(self):
        if self._assign_perm is None:
            from guardian.shortcuts import assign_perm as guardian_assign_perm
            self._assign_perm = guardian_assign_perm
        
        return self._assign_perm


    def test_group_model_locked_role_mapping(self):
        roles = {}

        for role in LOCKED_ROLES:
            roles[role] = self._create_user_and_group_with_permissions(
                name=role,
                permissions=LOCKED_ROLES[role]["permissions"]
            )
        
        self._run_migrations()

        for role in roles:
            permissions = LOCKED_ROLES[role]["permissions"]
            user, group = roles[role]

            for perm in permissions:
                self.assertTrue(user.has_perm(perm))

            self.assertEqual(GroupRole.objects.filter(group=group).count(), 1)
            self.assertTrue(self._has_role(group, role))


    def test_group_model_locked_role_mapping_with_dangling_permissions(self):
        permissions_to_add = \
            LOCKED_ROLES["galaxy.collection_admin"]["permissions"] + \
            LOCKED_ROLES["galaxy.execution_environment_admin"]["permissions"] + \
            LOCKED_ROLES["galaxy.collection_namespace_owner"]["permissions"] + \
            ["galaxy.view_user", "core.view_task"]

        user, group = self._create_user_and_group_with_permissions("test", permissions_to_add)

        # Add permissions directly to a group
        for perm in permissions_to_add:
            group.permissions.add(self._get_permission(perm))
        group.save()

        self._run_migrations()

        for perm in permissions_to_add:
            self.assertTrue(user.has_perm(perm))

        # content_admin contains perms for collection and EE admin
        expected_roles = [
            "galaxy.content_admin",
            "_permission:galaxy.view_user",
            "_permission:core.view_task",
        ]

        self.assertEqual(GroupRole.objects.filter(group=group).count(), len(expected_roles))
        
        for role in expected_roles:
            role_obj = Role.objects.get(name=role)
            self.assertEqual(GroupRole.objects.filter(group=group, role=role_obj).count(), 1)
            self.assertTrue(self._has_role(group, role))


    def test_group_permissions_post_migration(self):
        permissions_to_add = LOCKED_ROLES["galaxy.collection_admin"]["permissions"]

        _, group = self._create_user_and_group_with_permissions("test", permissions_to_add)

        # Add permissions directly to a group
        for perm in permissions_to_add:
            group.permissions.add(self._get_permission(perm))
        group.save()

        self.assertTrue(len(permissions_to_add) > 0)
        self.assertEqual(group.permissions.count(), len(permissions_to_add))

        self._run_migrations()

        expected_role = "galaxy.collection_admin"
        role_obj = Role.objects.get(name=expected_role)
        self.assertEqual(GroupRole.objects.filter(group=group).count(), 1)
        self.assertEqual(GroupRole.objects.filter(group=group, role=role_obj).count(), 1)
        self.assertTrue(self._has_role(group, expected_role))

        # check that group no longer has any permissions associated
        group.refresh_from_db()
        self.assertEqual(group.permissions.all().count(), 0)

        # check that assigning a role does not alter permissions
        perm_count_post_migration = group.permissions.all().count()
        new_role = "galaxy.collection_namespace_owner"
        assign_role(rolename=new_role, entity=group)
        group.refresh_from_db()
        self.assertTrue(self._has_role(group, new_role))
        self.assertEqual(group.permissions.all().count(), perm_count_post_migration)

    @skipIf(
        not is_guardian_installed(),
        "Django guardian is not installed."
    )
    def test_group_object_locked_role_mapping(self):
        namespace = Namespace.objects.create(name="my_namespace")
        container_namespace = ContainerNamespace.objects.create(name="my_container_ns")

        _, namespace_super_group = self._create_user_and_group_with_permissions(
            "ns_super_owner",
            ["galaxy.change_namespace"],
            obj=namespace
        )

        _, container_namespace_super_group = self._create_user_and_group_with_permissions(
            "cns_super_owner",
            ["container.change_containernamespace", "container.namespace_push_containerdistribution"],
            obj=container_namespace
        )

        ns_roles = ["galaxy.collection_namespace_owner"]
        c_ns_roles = [
            "galaxy.execution_environment_namespace_owner",
            "galaxy.execution_environment_collaborator"]

        ns_users = {}
        c_ns_users = {}

        for role in ns_roles:
            ns_users[role] = self._create_user_and_group_with_permissions(
                role, LOCKED_ROLES[role]["permissions"], obj=namespace)

        for role in c_ns_roles:
            c_ns_users[role] = self._create_user_and_group_with_permissions(
                role, LOCKED_ROLES[role]["permissions"], obj=container_namespace)

        self._run_migrations()

        # Verify locked role mapping works
        for role in ns_users:
            permissions = LOCKED_ROLES[role]["permissions"]
            user, group = ns_users[role]
            
            for perm in permissions:
                self.assertTrue(user.has_perm(perm, obj=namespace))
                self.assertFalse(user.has_perm(perm))
            
            self.assertEqual(GroupRole.objects.filter(group=group).count(), 1)
            self.assertTrue(self._has_role(group, role, obj=namespace))

        for role in c_ns_users:
            permissions = LOCKED_ROLES[role]["permissions"]
            user, group = c_ns_users[role]
            
            for perm in permissions:
                self.assertTrue(user.has_perm(perm, obj=container_namespace))
                self.assertFalse(user.has_perm(perm))
            
            self.assertEqual(GroupRole.objects.filter(group=group).count(), 1)
            self.assertTrue(self._has_role(group, role, obj=container_namespace))
    
        # Verify super permissions work
        self.assertTrue(self._has_role(namespace_super_group, "galaxy.collection_namespace_owner", namespace))
        self.assertTrue(
            self._has_role(
                container_namespace_super_group,
                "galaxy.execution_environment_namespace_owner",
                container_namespace)
        )

    @skipIf(
        not is_guardian_installed(),
        "Django guardian is not installed."
    )
    def test_user_role(self):
        ns = ContainerNamespace.objects.create(name="my_container_namespace")
        user = User.objects.create(username="test")

        perm = self._get_permission("container.change_containernamespace")
        self._get_assign_perm(perm, user, obj=ns)
        c_type = ContentType.objects.get_for_model(ContainerNamespace)

        self._run_migrations()

        role_obj = Role.objects.get(name="galaxy.execution_environment_namespace_owner")
        has_role = UserRole.objects.filter(
                user=user,
                role=role_obj,
                content_type=c_type,
                object_id=ns.pk
            ).exists()

        self.assertTrue(has_role)


    def test_empty_groups(self):
        user, group = self._create_user_and_group_with_permissions("test", [])

        self._run_migrations()
        
        self.assertEqual(UserRole.objects.filter(user=user).count(), 0)
        self.assertEqual(GroupRole.objects.filter(group=group).count(), 0)
