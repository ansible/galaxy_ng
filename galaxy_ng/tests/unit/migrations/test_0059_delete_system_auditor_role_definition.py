from importlib import import_module

from django.test import TestCase
from django.apps import apps
from django.db import migrations

from ansible_base.rbac import permission_registry

from galaxy_ng.app.models import User, Team, Organization
from galaxy_ng.app.migrations._dab_rbac import (
    repair_mismatched_role_assignments,
    filter_mismatched_assignments,
)


class TestDeleteSystemAuditorRoleDefinitionMigration(TestCase):
    """Test migration 0059_delete_system_auditor_role_definition."""

    def test_delete_system_auditor_role_definition_exists(self):
        """Test deleting System Auditor role definition when it exists."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")

        # Create the System Auditor role that should be deleted
        RoleDefinition.objects.create_from_permissions(
            name="System Auditor",
            permissions=["view_namespace"],
            managed=True,
        )

        # Verify it exists
        self.assertTrue(RoleDefinition.objects.filter(name="System Auditor").exists())

        # Run the migration
        migration_module = import_module(
            'galaxy_ng.app.migrations.0059_delete_system_auditor_role_definition'
        )
        migration_module.delete_system_auditor_role_definition(apps, None)

        # Verify it was deleted
        self.assertFalse(RoleDefinition.objects.filter(name="System Auditor").exists())

    def test_delete_system_auditor_role_definition_not_exists(self):
        """Test migration when System Auditor role definition doesn't exist."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")

        # Ensure no System Auditor role exists
        RoleDefinition.objects.filter(name="System Auditor").delete()

        # Run the migration (should not raise an error)
        migration_module = import_module(
            'galaxy_ng.app.migrations.0059_delete_system_auditor_role_definition'
        )
        migration_module.delete_system_auditor_role_definition(apps, None)

        # Verify it still doesn't exist
        self.assertFalse(RoleDefinition.objects.filter(name="System Auditor").exists())

    def test_migration_dependencies(self):
        """Test that migration has correct dependencies."""
        migration_module = import_module(
            'galaxy_ng.app.migrations.0059_delete_system_auditor_role_definition'
        )
        Migration = migration_module.Migration

        assert hasattr(Migration, 'dependencies')
        assert ("galaxy", "0058_remove_galaxy_team_member_role") in Migration.dependencies
        assert ("dab_rbac", "0003_alter_dabpermission_codename_and_more") in Migration.dependencies

    def test_migration_operations(self):
        """Test that migration has correct operations."""
        migration_module = import_module(
            'galaxy_ng.app.migrations.0059_delete_system_auditor_role_definition'
        )
        Migration = migration_module.Migration
        delete_system_auditor_role_definition = (
            migration_module.delete_system_auditor_role_definition
        )

        assert hasattr(Migration, 'operations')
        assert len(Migration.operations) == 2

        operation = Migration.operations[0]
        assert isinstance(operation, migrations.RunPython)

        # The RunPython operation should reference our function
        assert operation.code == delete_system_auditor_role_definition
        assert operation.reverse_code == migrations.RunPython.noop


class TestRepairMismatchedRoleAssignmentsMigration(TestCase):
    """Test repair_mismatched_role_assignments migration function."""

    def setUp(self):
        """Set up test data."""
        self.org = Organization.objects.create(name="Test Org")
        self.team = Team.objects.create(name="Test Team", organization=self.org)
        self.user1 = User.objects.create(username="testuser1")
        self.user2 = User.objects.create(username="testuser2")

    def test_no_mismatched_assignments(self):
        """Test when there are no mismatched assignments."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Create a global role (no content_type)
        global_role = RoleDefinition.objects.create_from_permissions(
            name="GlobalRole",
            permissions=["view_namespace"],
            content_type=None,
            managed=False,
        )

        # Create a global assignment (matches the role)
        assignment = global_role.give_global_permission(self.user1)
        assert global_role.content_type is None
        assert assignment.content_type is None
        assert assignment.role_definition is global_role
        assert global_role.user_assignments.count() == 1

        # Verify query does NOT find this assignment (both have None, so they match)
        mismatched = filter_mismatched_assignments(RoleUserAssignment.objects.all())
        self.assertEqual(mismatched.count(), 0)
        self.assertFalse(mismatched.filter(id=assignment.id).exists())

        initial_role_count = RoleDefinition.objects.count()

        # Run migration
        repair_mismatched_role_assignments(apps, None)

        # No new roles should be created
        self.assertEqual(RoleDefinition.objects.count(), initial_role_count)

        # Assignment should still exist
        self.assertTrue(
            RoleUserAssignment.objects.filter(
                role_definition=global_role,
                user=self.user1
            ).exists()
        )

    def test_user_assignment_with_mismatched_content_type(self):
        """Test fixing user assignment with null content_type on role with specific content_type."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Create a role with a specific content_type
        team_ct = permission_registry.content_type_model.objects.get_for_model(Team)
        team_role = RoleDefinition.objects.create_from_permissions(
            name="TeamRole",
            permissions=["view_team"],
            content_type=team_ct,
            managed=False,
        )

        # Create a global assignment (mismatched - should be object-level)
        # NOTE: This intentionally creates an invalid state for testing
        # In production code, give_permission should always be used
        assignment = RoleUserAssignment.objects.create(
            role_definition=team_role,
            user=self.user1,
            content_type=None,
            object_id=None,
        )

        # Verify query finds the mismatched assignment
        mismatched = filter_mismatched_assignments(RoleUserAssignment.objects.all())
        self.assertEqual(mismatched.count(), 1)
        self.assertTrue(mismatched.filter(id=assignment.id).exists())

        # Run migration
        repair_mismatched_role_assignments(apps, None)

        # New global role should be created
        new_role = RoleDefinition.objects.get(name="TeamRole_global")
        self.assertIsNone(new_role.content_type)
        self.assertFalse(new_role.managed)
        self.assertIn("Auto-fixed from TeamRole", new_role.description)

        # Old assignment should be gone
        self.assertFalse(
            RoleUserAssignment.objects.filter(id=assignment.id).exists()
        )

        # New assignment should exist
        self.assertTrue(
            RoleUserAssignment.objects.filter(
                role_definition=new_role,
                user=self.user1,
                content_type=None,
                object_id=None,
            ).exists()
        )

    def test_team_assignment_with_mismatched_content_type(self):
        """Test fixing team assignment with mismatched content_type."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleTeamAssignment = apps.get_model("dab_rbac", "RoleTeamAssignment")

        # Create a role with a specific content_type
        team_ct = permission_registry.content_type_model.objects.get_for_model(Team)
        team_role = RoleDefinition.objects.create_from_permissions(
            name="SpecificRole",
            permissions=["view_team"],
            content_type=team_ct,
            managed=False,
        )

        # Create a global assignment (mismatched)
        # NOTE: This intentionally creates an invalid state for testing
        # In production code, give_permission should always be used
        assignment = RoleTeamAssignment.objects.create(
            role_definition=team_role,
            team=self.team,
            content_type=None,
            object_id=None,
        )

        # Verify query finds the mismatched assignment
        mismatched = filter_mismatched_assignments(RoleTeamAssignment.objects.all())
        self.assertEqual(mismatched.count(), 1)
        self.assertTrue(mismatched.filter(id=assignment.id).exists())

        # Run migration
        repair_mismatched_role_assignments(apps, None)

        # New global role should be created
        new_role = RoleDefinition.objects.get(name="SpecificRole_global")
        self.assertIsNone(new_role.content_type)

        # Old assignment should be gone
        self.assertFalse(
            RoleTeamAssignment.objects.filter(id=assignment.id).exists()
        )

        # New assignment should exist
        self.assertTrue(
            RoleTeamAssignment.objects.filter(
                role_definition=new_role,
                team=self.team,
                content_type=None,
                object_id=None,
            ).exists()
        )

    def test_mixed_user_and_team_assignments_on_same_role(self):
        """Test fixing both user and team assignments on the same role."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")
        RoleTeamAssignment = apps.get_model("dab_rbac", "RoleTeamAssignment")

        # Create a role with specific content_type
        team_ct = permission_registry.content_type_model.objects.get_for_model(Team)
        mixed_role = RoleDefinition.objects.create_from_permissions(
            name="MixedRole",
            permissions=["view_team"],
            content_type=team_ct,
            managed=False,
        )

        # Create mismatched assignments for both user and team
        # NOTE: This intentionally creates an invalid state for testing
        # In production code, give_permission should always be used
        user_assignment = RoleUserAssignment.objects.create(
            role_definition=mixed_role,
            user=self.user1,
            content_type=None,
            object_id=None,
        )
        team_assignment = RoleTeamAssignment.objects.create(
            role_definition=mixed_role,
            team=self.team,
            content_type=None,
            object_id=None,
        )

        # Verify queries find both mismatched assignments
        mismatched_users = filter_mismatched_assignments(RoleUserAssignment.objects.all())
        mismatched_teams = filter_mismatched_assignments(RoleTeamAssignment.objects.all())
        self.assertEqual(mismatched_users.count(), 1)
        self.assertEqual(mismatched_teams.count(), 1)
        self.assertTrue(mismatched_users.filter(id=user_assignment.id).exists())
        self.assertTrue(mismatched_teams.filter(id=team_assignment.id).exists())

        # Run migration
        repair_mismatched_role_assignments(apps, None)

        # Only one new role should be created (shared by both)
        self.assertEqual(
            RoleDefinition.objects.filter(name="MixedRole_global").count(),
            1
        )
        new_role = RoleDefinition.objects.get(name="MixedRole_global")

        # Old assignments should be gone
        self.assertFalse(
            RoleUserAssignment.objects.filter(id=user_assignment.id).exists()
        )
        self.assertFalse(
            RoleTeamAssignment.objects.filter(id=team_assignment.id).exists()
        )

        # New assignments should exist for both
        self.assertTrue(
            RoleUserAssignment.objects.filter(
                role_definition=new_role,
                user=self.user1
            ).exists()
        )
        self.assertTrue(
            RoleTeamAssignment.objects.filter(
                role_definition=new_role,
                team=self.team
            ).exists()
        )

    def test_skip_assignment_with_non_null_object_id(self):
        """Test that assignments with non-null object_id are skipped."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Create a role with specific content_type
        team_ct = permission_registry.content_type_model.objects.get_for_model(Team)
        skip_role = RoleDefinition.objects.create_from_permissions(
            name="SkipRole",
            permissions=["view_team"],
            content_type=team_ct,
            managed=False,
        )

        # Create assignment with mismatched content_type BUT non-null object_id
        # This is unexpected and should be skipped
        # NOTE: This intentionally creates an invalid state for testing
        # In production code, give_permission should always be used
        assignment = RoleUserAssignment.objects.create(
            role_definition=skip_role,
            user=self.user1,
            content_type=None,  # Mismatched
            object_id=self.team.id,  # Non-null, unexpected
        )

        initial_role_count = RoleDefinition.objects.count()

        # Run migration
        repair_mismatched_role_assignments(apps, None)

        # No new role should be created (skipped)
        self.assertEqual(RoleDefinition.objects.count(), initial_role_count)

        # Assignment should still exist (not deleted)
        self.assertTrue(
            RoleUserAssignment.objects.filter(id=assignment.id).exists()
        )

    def test_skip_role_with_no_permissions(self):
        """Test that roles with no permissions are skipped."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Create a role with content_type but NO permissions
        team_ct = permission_registry.content_type_model.objects.get_for_model(Team)
        empty_role = RoleDefinition.objects.create(
            name="EmptyRole",
            description="Empty role",
            content_type=team_ct,
            managed=False,
        )

        # Create a mismatched assignment
        # NOTE: This intentionally creates an invalid state for testing
        # In production code, give_permission should always be used
        assignment = RoleUserAssignment.objects.create(
            role_definition=empty_role,
            user=self.user1,
            content_type=None,
            object_id=None,
        )

        initial_role_count = RoleDefinition.objects.count()

        # Run migration
        repair_mismatched_role_assignments(apps, None)

        # No new role should be created (skipped due to no permissions)
        self.assertEqual(RoleDefinition.objects.count(), initial_role_count)

        # Assignment should still exist (not deleted)
        self.assertTrue(
            RoleUserAssignment.objects.filter(id=assignment.id).exists()
        )

    def test_multiple_roles_needing_repair(self):
        """Test processing multiple roles with mismatched assignments."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")
        Namespace = apps.get_model('galaxy', 'Namespace')

        # Create two different roles with specific content_types
        team_ct = permission_registry.content_type_model.objects.get_for_model(Team)
        namespace_ct = permission_registry.content_type_model.objects.get_for_model(Namespace)

        role1 = RoleDefinition.objects.create_from_permissions(
            name="Role1",
            permissions=["view_team"],
            content_type=team_ct,
            managed=False,
        )

        role2 = RoleDefinition.objects.create_from_permissions(
            name="Role2",
            permissions=["view_namespace"],
            content_type=namespace_ct,
            managed=False,
        )

        # Create mismatched assignments for each
        # NOTE: This intentionally creates an invalid state for testing
        # In production code, give_permission should always be used
        RoleUserAssignment.objects.create(
            role_definition=role1,
            user=self.user1,
            content_type=None,
            object_id=None,
        )
        RoleUserAssignment.objects.create(
            role_definition=role2,
            user=self.user2,
            content_type=None,
            object_id=None,
        )

        # Run migration
        repair_mismatched_role_assignments(apps, None)

        # Two new global roles should be created
        self.assertTrue(RoleDefinition.objects.filter(name="Role1_global").exists())
        self.assertTrue(RoleDefinition.objects.filter(name="Role2_global").exists())

        new_role1 = RoleDefinition.objects.get(name="Role1_global")
        new_role2 = RoleDefinition.objects.get(name="Role2_global")

        # Each user should have their respective new role
        self.assertTrue(
            RoleUserAssignment.objects.filter(
                role_definition=new_role1,
                user=self.user1
            ).exists()
        )
        self.assertTrue(
            RoleUserAssignment.objects.filter(
                role_definition=new_role2,
                user=self.user2
            ).exists()
        )

    def test_migration_preserves_permissions(self):
        """Test that migration correctly copies permissions to new role."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")
        Namespace = apps.get_model("galaxy", "Namespace")

        # Create a role with multiple permissions
        namespace_ct = permission_registry.content_type_model.objects.get_for_model(Namespace)
        multi_perm_role = RoleDefinition.objects.create_from_permissions(
            name="MultiPermRole",
            permissions=["view_namespace", "change_namespace", "delete_namespace"],
            content_type=namespace_ct,
            managed=False,
        )

        # Create mismatched assignment
        # NOTE: This intentionally creates an invalid state for testing
        # In production code, give_permission should always be used
        RoleUserAssignment.objects.create(
            role_definition=multi_perm_role,
            user=self.user1,
            content_type=None,
            object_id=None,
        )

        # Run migration
        repair_mismatched_role_assignments(apps, None)

        # Check new role has all permissions
        new_role = RoleDefinition.objects.get(name="MultiPermRole_global")
        permission_codenames = [p.codename for p in new_role.permissions.all()]

        self.assertEqual(len(permission_codenames), 3)
        self.assertIn("view_namespace", permission_codenames)
        self.assertIn("change_namespace", permission_codenames)
        self.assertIn("delete_namespace", permission_codenames)

    def test_migration_idempotency(self):
        """Test that running the migration multiple times is safe."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Create a role with specific content_type
        team_ct = permission_registry.content_type_model.objects.get_for_model(Team)
        role = RoleDefinition.objects.create_from_permissions(
            name="IdempotentRole",
            permissions=["view_team"],
            content_type=team_ct,
            managed=False,
        )

        # Create mismatched assignment
        # NOTE: This intentionally creates an invalid state for testing
        # In production code, give_permission should always be used
        RoleUserAssignment.objects.create(
            role_definition=role,
            user=self.user1,
            content_type=None,
            object_id=None,
        )

        # Run migration first time
        repair_mismatched_role_assignments(apps, None)

        # Verify new role created
        self.assertTrue(RoleDefinition.objects.filter(name="IdempotentRole_global").exists())
        new_role = RoleDefinition.objects.get(name="IdempotentRole_global")
        first_run_assignment_count = RoleUserAssignment.objects.filter(
            role_definition=new_role
        ).count()

        # Run migration second time (should be safe)
        repair_mismatched_role_assignments(apps, None)

        # Assignment count should be unchanged
        second_run_assignment_count = RoleUserAssignment.objects.filter(
            role_definition=new_role
        ).count()
        self.assertEqual(first_run_assignment_count, second_run_assignment_count)

        # Only one global role should exist
        self.assertEqual(
            RoleDefinition.objects.filter(name="IdempotentRole_global").count(),
            1
        )

    def test_filter_mismatched_assignments(self):
        """Test that filter only returns role with CT + assignment without CT."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")
        RoleTeamAssignment = apps.get_model("dab_rbac", "RoleTeamAssignment")

        team_ct = permission_registry.content_type_model.objects.get_for_model(Team)

        # Create roles
        global_role = RoleDefinition.objects.create_from_permissions(
            name="GlobalRole", permissions=["view_namespace"], content_type=None, managed=False
        )
        specific_role = RoleDefinition.objects.create_from_permissions(
            name="SpecificRole", permissions=["view_team"], content_type=team_ct, managed=False
        )

        # Create mismatched assignments (should be returned)
        mismatched_user = RoleUserAssignment.objects.create(
            role_definition=specific_role, user=self.user1, content_type=None, object_id=None
        )
        mismatched_team = RoleTeamAssignment.objects.create(
            role_definition=specific_role, team=self.team, content_type=None, object_id=None
        )

        # Create matched assignments (should NOT be returned)
        RoleUserAssignment.objects.create(
            role_definition=global_role, user=self.user1, content_type=None, object_id=None
        )
        RoleUserAssignment.objects.create(
            role_definition=specific_role,
            user=self.user2,
            content_type=team_ct,
            object_id=self.team.id
        )

        # Test user assignments
        user_mismatched = filter_mismatched_assignments(RoleUserAssignment.objects.all())
        self.assertEqual(user_mismatched.count(), 1)
        self.assertEqual(user_mismatched.first().id, mismatched_user.id)

        # Test team assignments
        team_mismatched = filter_mismatched_assignments(RoleTeamAssignment.objects.all())
        self.assertEqual(team_mismatched.count(), 1)
        self.assertEqual(team_mismatched.first().id, mismatched_team.id)
