"""
Integration tests for Galaxy Team Member to Team Member role transition.

These tests verify the complete transition from "Galaxy Team Member" to "Team Member"
role across different scenarios including migration, signal handling, and edge cases.
"""

from importlib import import_module
from unittest.mock import patch

from django.test import TestCase
from django.apps import apps

from ansible_base.rbac import permission_registry

from galaxy_ng.app.models import User, Team
from galaxy_ng.app.models.organization import Organization


class TestGalaxyTeamMemberRoleTransition(TestCase):
    """Integration tests for the complete role transition process."""

    def setUp(self):
        """Set up test data for integration tests."""
        self.org = Organization.objects.create(name="Test Organization")
        self.team = Team.objects.create(name="Test Team", organization=self.org)
        self.user1 = User.objects.create(username="testuser1")
        self.user2 = User.objects.create(username="testuser2")
        self.admin_user = User.objects.create(username="admin", is_superuser=True)

    def _run_migration(self):
        """Helper to run the migration."""
        migration = import_module("galaxy_ng.app.migrations.0058_remove_galaxy_team_member_role")
        return migration.remove_galaxy_team_member_role(apps, None)

    def test_complete_migration_workflow(self):
        """Test the complete migration workflow from Galaxy Team Member to Team Member."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")
        RoleTeamAssignment = apps.get_model("dab_rbac", "RoleTeamAssignment")
        ObjectRole = apps.get_model("dab_rbac", "ObjectRole")

        # Step 1: Create initial state with Galaxy Team Member role
        galaxy_role = RoleDefinition.objects.create_from_permissions(
            name="Galaxy Team Member",
            permissions=["view_team"],
            managed=True,
        )

        team_role = RoleDefinition.objects.get(
            name="Team Member",
        )

        # Step 2: Create various types of assignments
        RoleUserAssignment.objects.create(
            role_definition=galaxy_role,
            user=self.user1,
            object_id=self.team.id,
            content_type=permission_registry.content_type_model.objects.get_for_model(Team),
        )

        RoleTeamAssignment.objects.create(
            role_definition=galaxy_role,
            team=self.team,
            object_id=self.team.id,
            content_type=permission_registry.content_type_model.objects.get_for_model(Team),
        )

        ObjectRole.objects.create(
            role_definition=galaxy_role,
            object_id=self.team.id,
            content_type=permission_registry.content_type_model.objects.get_for_model(Team),
        )

        # Step 3: Verify pre-migration state
        pre_migration_counts = {
            "user_assignments": RoleUserAssignment.objects.filter(
                role_definition=galaxy_role
            ).count(),
            "team_assignments": RoleTeamAssignment.objects.filter(
                role_definition=galaxy_role
            ).count(),
            "object_roles": ObjectRole.objects.filter(role_definition=galaxy_role).count(),
            "galaxy_role_exists": RoleDefinition.objects.filter(name="Galaxy Team Member").exists(),
            "team_role_exists": RoleDefinition.objects.filter(name="Team Member").exists(),
        }

        self.assertEqual(pre_migration_counts["user_assignments"], 1)
        self.assertEqual(pre_migration_counts["team_assignments"], 1)
        self.assertEqual(pre_migration_counts["object_roles"], 1)
        self.assertTrue(pre_migration_counts["galaxy_role_exists"])
        self.assertTrue(pre_migration_counts["team_role_exists"])

        # Step 4: Run migration
        self._run_migration()

        # Step 5: Verify post-migration state
        post_migration_counts = {
            "user_assignments": RoleUserAssignment.objects.filter(
                role_definition=team_role
            ).count(),
            "team_assignments": RoleTeamAssignment.objects.filter(
                role_definition=team_role
            ).count(),
            "object_roles": ObjectRole.objects.filter(role_definition=team_role).count(),
            "galaxy_role_exists": RoleDefinition.objects.filter(name="Galaxy Team Member").exists(),
            "team_role_exists": RoleDefinition.objects.filter(name="Team Member").exists(),
            "orphaned_assignments": (
                RoleUserAssignment.objects.filter(role_definition_id=galaxy_role.id).count()
                + RoleTeamAssignment.objects.filter(role_definition_id=galaxy_role.id).count()
                + ObjectRole.objects.filter(role_definition_id=galaxy_role.id).count()
            ),
        }

        # All assignments should be migrated to Team Member role
        self.assertEqual(post_migration_counts["user_assignments"], 1)
        self.assertEqual(post_migration_counts["team_assignments"], 1)
        self.assertEqual(post_migration_counts["object_roles"], 1)

        # Galaxy Team Member role should be deleted
        self.assertFalse(post_migration_counts["galaxy_role_exists"])

        # Team Member role should still exist
        self.assertTrue(post_migration_counts["team_role_exists"])

        # No orphaned assignments should remain
        self.assertEqual(post_migration_counts["orphaned_assignments"], 0)

    def test_migration_with_duplicate_role_assignments(self):
        """Test migration when a user has both Galaxy Team Member and Team Member roles."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")
        ObjectRole = apps.get_model("dab_rbac", "ObjectRole")

        # Create both role definitions
        galaxy_role = RoleDefinition.objects.create_from_permissions(
            name="Galaxy Team Member",
            permissions=["view_team"],
            managed=True,
        )

        team_role = RoleDefinition.objects.get(
            name="Team Member",
        )

        # Create object roles for both definitions
        galaxy_obj_role = ObjectRole.objects.create(
            role_definition=galaxy_role,
            object_id=self.team.id,
            content_type=permission_registry.content_type_model.objects.get_for_model(Team),
        )

        team_obj_role = ObjectRole.objects.create(
            role_definition=team_role,
            object_id=self.team.id,
            content_type=permission_registry.content_type_model.objects.get_for_model(Team),
        )

        # user1 has BOTH Galaxy Team Member AND Team Member roles (duplicate scenario)
        RoleUserAssignment.objects.create(
            role_definition=galaxy_role,
            user=self.user1,
            object_id=self.team.id,
            content_type=permission_registry.content_type_model.objects.get_for_model(Team),
        )

        RoleUserAssignment.objects.create(
            role_definition=team_role,
            user=self.user1,
            object_id=self.team.id,
            content_type=permission_registry.content_type_model.objects.get_for_model(Team),
        )

        # user2 has ONLY Galaxy Team Member role
        RoleUserAssignment.objects.create(
            role_definition=galaxy_role,
            user=self.user2,
            object_id=self.team.id,
            content_type=permission_registry.content_type_model.objects.get_for_model(Team),
        )

        # Verify pre-migration state
        galaxy_user_assignments = RoleUserAssignment.objects.filter(
            role_definition=galaxy_role
        ).count()
        team_user_assignments = RoleUserAssignment.objects.filter(
            role_definition=team_role
        ).count()

        self.assertEqual(galaxy_user_assignments, 2)  # user1 and user2
        self.assertEqual(team_user_assignments, 1)  # only user1

        # Run migration
        self._run_migration()

        # Verify post-migration state
        # Galaxy Team Member role should be deleted
        self.assertFalse(RoleDefinition.objects.filter(name="Galaxy Team Member").exists())

        # Team Member role should still exist
        self.assertTrue(RoleDefinition.objects.filter(name="Team Member").exists())

        # Both users should have Team Member role now
        team_assignments = RoleUserAssignment.objects.filter(
            role_definition=team_role,
            object_id=self.team.id
        )
        self.assertEqual(team_assignments.count(), 2)

        # Verify both users are in the assignments
        assigned_users = set(team_assignments.values_list('user_id', flat=True))
        self.assertEqual(assigned_users, {self.user1.id, self.user2.id})

        # user1 should NOT have duplicate Team Member assignments
        user1_team_assignments = RoleUserAssignment.objects.filter(
            role_definition=team_role,
            user=self.user1,
            object_id=self.team.id
        ).count()
        self.assertEqual(user1_team_assignments, 1)

        # No orphaned assignments should remain
        orphaned_count = (
            RoleUserAssignment.objects.filter(role_definition_id=galaxy_role.id).count()
            + ObjectRole.objects.filter(role_definition_id=galaxy_role.id).count()
        )
        self.assertEqual(orphaned_count, 0)

    def test_migration_idempotency(self):
        """Test that running the migration multiple times is safe."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Create initial state
        team_role = RoleDefinition.objects.get(
            name="Team Member",
        )

        RoleUserAssignment.objects.create(
            role_definition=team_role,
            user=self.user1,
            object_id=self.team.id,
            content_type=permission_registry.content_type_model.objects.get_for_model(Team),
        )

        # Run migration (should be no-op since Galaxy Team Member doesn't exist)
        initial_count = RoleUserAssignment.objects.filter(role_definition=team_role).count()

        self._run_migration()

        # Count should be unchanged
        final_count = RoleUserAssignment.objects.filter(role_definition=team_role).count()
        self.assertEqual(initial_count, final_count)

        # Team Member role should still exist
        self.assertTrue(RoleDefinition.objects.filter(name="Team Member").exists())

    def test_backward_compatibility_constants(self):
        """Test that signal handler constants are properly updated."""
        from galaxy_ng.app.signals.handlers import SHARED_TEAM_ROLE

        # Verify the constant is set to the new role name
        self.assertEqual(SHARED_TEAM_ROLE, "Team Member")

        # Verify the old constant is removed by checking the module's attributes
        import galaxy_ng.app.signals.handlers as handlers_module

        self.assertFalse(
            hasattr(handlers_module, "TEAM_MEMBER_ROLE"),
            "TEAM_MEMBER_ROLE constant should have been removed",
        )

    def test_serializer_compatibility(self):
        """Test that serializers work with the new role names."""
        from galaxy_ng.app.api.ui.v2.serializers import UserDetailSerializer

        # Create a user with team membership
        self.team.group.user_set.add(self.user1)

        # Mock the role definitions and assignments
        with (
            patch("galaxy_ng.app.api.ui.v2.serializers.RoleDefinition") as mock_role_def,
            patch("galaxy_ng.app.api.ui.v2.serializers.RoleUserAssignment") as mock_assignment,
        ):
            # Mock role definitions to return Team Member role
            mock_role_def.objects.filter.return_value.values_list.return_value = [1]

            # Mock assignments
            mock_assignment.objects.filter.return_value.values_list.return_value = [self.team.id]

            # Create serializer
            serializer = UserDetailSerializer(self.user1)

            # Should work without errors and include team information
            data = serializer.data
            self.assertIn("teams", data)
