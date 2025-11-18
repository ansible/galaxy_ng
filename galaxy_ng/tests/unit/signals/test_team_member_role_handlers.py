"""
Unit tests for team member role signal handlers.

These tests cover the signal handlers that manage the relationship between
DAB RBAC "Team Member" role assignments and Django group membership.
"""

from unittest.mock import Mock, patch

import pytest
from django.test import TestCase
from django.contrib.auth.models import Group

from galaxy_ng.app.models import User, Team
from galaxy_ng.app.models.organization import Organization


class TestTeamMemberRoleSignalHandlers(TestCase):
    """Test cases for team member role signal handlers."""

    def setUp(self):
        """Set up test data."""
        self.org = Organization.objects.create(name="Test Org")
        self.team = Team.objects.create(name="Test Team", organization=self.org)
        self.user = User.objects.create(username="testuser")
        self.group = self.team.group

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    def test_copy_dab_user_role_assignment_team_member(
        self, mock_dab_signals, mock_signal_in_progress
    ):
        """Test that Team Member role assignment adds user to group."""
        from galaxy_ng.app.signals.handlers import copy_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment

        # Mock signal not in progress
        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Create Team Member role definition
        role_def = Mock()
        role_def.name = "Team Member"

        # Create mock assignment
        assignment = Mock(spec=RoleUserAssignment)
        assignment.role_definition = role_def
        assignment.user = self.user
        assignment.content_object = self.team

        # Verify user not in group initially
        self.assertNotIn(self.user, self.group.user_set.all())

        # Call signal handler
        copy_dab_user_role_assignment(None, assignment, created=True)

        # Verify user was added to group
        self.assertIn(self.user, self.group.user_set.all())

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    def test_copy_dab_user_role_assignment_other_role(
        self, mock_dab_signals, mock_signal_in_progress
    ):
        """Test that non-Team Member role assignment doesn't add user to group."""
        from galaxy_ng.app.signals.handlers import copy_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment

        # Mock signal not in progress
        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Create other role definition
        role_def = Mock()
        role_def.name = "Other Role"

        # Create mock assignment
        assignment = Mock(spec=RoleUserAssignment)
        assignment.role_definition = role_def
        assignment.user = self.user
        assignment.content_object = self.team

        # Verify user not in group initially
        self.assertNotIn(self.user, self.group.user_set.all())

        # Mock _apply_dab_assignment to verify it's called
        with patch("galaxy_ng.app.signals.handlers._apply_dab_assignment") as mock_apply:
            copy_dab_user_role_assignment(None, assignment, created=True)
            mock_apply.assert_called_once_with(assignment)

        # Verify user was not added to group directly
        self.assertNotIn(self.user, self.group.user_set.all())

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    @patch("galaxy_ng.app.signals.handlers.RoleUserAssignment")
    def test_delete_dab_user_role_assignment_with_other_assignments(
        self, mock_assignment_model, mock_dab_signals, mock_signal_in_progress
    ):
        """Test that Team Member role deletion keeps user in group when other assignments exist."""
        from galaxy_ng.app.signals.handlers import delete_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment

        # Mock signal not in progress
        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Add user to group initially
        self.group.user_set.add(self.user)
        self.assertIn(self.user, self.group.user_set.all())

        # Create Team Member role definition
        role_def = Mock()
        role_def.name = "Team Member"

        # Create mock assignment
        assignment = Mock(spec=RoleUserAssignment)
        assignment.role_definition = role_def
        assignment.user = self.user
        assignment.content_object = self.team
        assignment.object_id = self.team.id

        # Mock other assignments exist
        mock_assignment_model.objects.filter.return_value.exists.return_value = True

        # Call signal handler
        delete_dab_user_role_assignment(None, assignment)

        # Verify user was NOT removed from group
        self.assertIn(self.user, self.group.user_set.all())

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    def test_delete_dab_user_role_assignment_no_content_object(
        self, mock_dab_signals, mock_signal_in_progress
    ):
        """Test that Team Member role deletion with no content_object is handled gracefully."""
        from galaxy_ng.app.signals.handlers import delete_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment

        # Mock signal not in progress
        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Create Team Member role definition
        role_def = Mock()
        role_def.name = "Team Member"

        # Create mock assignment with no content_object
        assignment = Mock(spec=RoleUserAssignment)
        assignment.role_definition = role_def
        assignment.user = self.user
        assignment.content_object = None
        assignment.object_id = self.team.id

        # Mock _unapply_dab_assignment to verify it's called
        with patch("galaxy_ng.app.signals.handlers._unapply_dab_assignment") as mock_unapply:
            delete_dab_user_role_assignment(None, assignment)
            mock_unapply.assert_called_once_with(assignment)

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.RoleDefinition")
    @patch("galaxy_ng.app.signals.handlers.RoleUserAssignment")
    def test_copy_dab_group_to_role_simplified(
        self, mock_assignment_model, mock_role_def, mock_signal_in_progress
    ):
        """
        Test the simplified copy_dab_group_to_role function that only handles Team Member role.
        """
        from galaxy_ng.app.signals.handlers import copy_dab_group_to_role

        # Mock signal not in progress
        mock_signal_in_progress.return_value = False

        # Mock Team Member role definition
        mock_team_member_rd = Mock()
        mock_team_member_rd.name = "Team Member"
        mock_role_def.objects.get.return_value = mock_team_member_rd

        # Mock existing assignments
        mock_assignment_model.objects.filter.return_value = []

        # Add user to group
        self.group.user_set.add(self.user)

        # Call the handler
        copy_dab_group_to_role(
            instance=self.user,
            action="post_add",
            model=Group,
            pk_set={self.group.pk},
            reverse=False,
        )

        # Verify Team Member role was fetched
        mock_role_def.objects.get.assert_called_with(name="Team Member")

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    def test_signal_handler_skips_when_signal_in_progress(self, mock_signal_in_progress):
        """Test that signal handlers skip processing when rbac signal is in progress."""
        from galaxy_ng.app.signals.handlers import copy_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment

        # Mock signal in progress
        mock_signal_in_progress.return_value = True

        # Create mock assignment
        assignment = Mock(spec=RoleUserAssignment)

        # Call signal handler - should return early without processing
        result = copy_dab_user_role_assignment(None, assignment, created=True)

        # Verify it returned early (None)
        self.assertIsNone(result)

    def test_team_role_constants(self):
        """Test that team role constants are set correctly."""
        from galaxy_ng.app.signals.handlers import TEAM_ROLES, SHARED_TEAM_ROLE

        # TEAM_ROLES should contain both team roles that use Django Group membership
        self.assertEqual(TEAM_ROLES, ["Team Member", "Team Admin"])

        # SHARED_TEAM_ROLE should reference Team Member for backward compatibility
        self.assertEqual(SHARED_TEAM_ROLE, "Team Member")

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    def test_copy_dab_team_role_assignment(self, mock_dab_signals, mock_signal_in_progress):
        """Test that team role assignments are properly handled."""
        from galaxy_ng.app.signals.handlers import copy_dab_team_role_assignment
        from ansible_base.rbac.models import RoleTeamAssignment

        # Mock signal not in progress
        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Create mock team assignment
        assignment = Mock(spec=RoleTeamAssignment)

        # Mock _apply_dab_assignment to verify it's called
        with patch("galaxy_ng.app.signals.handlers._apply_dab_assignment") as mock_apply:
            copy_dab_team_role_assignment(None, assignment, created=True)
            mock_apply.assert_called_once_with(assignment)

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    def test_delete_dab_team_role_assignment(self, mock_dab_signals, mock_signal_in_progress):
        """Test that team role assignment deletions are properly handled."""
        from galaxy_ng.app.signals.handlers import delete_dab_team_role_assignment
        from ansible_base.rbac.models import RoleTeamAssignment

        # Mock signal not in progress
        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Create mock team assignment
        assignment = Mock(spec=RoleTeamAssignment)

        # Mock _unapply_dab_assignment to verify it's called
        with patch("galaxy_ng.app.signals.handlers._unapply_dab_assignment") as mock_unapply:
            delete_dab_team_role_assignment(None, assignment)
            mock_unapply.assert_called_once_with(assignment)


class TestTeamAdminRoleSignalHandlers(TestCase):
    """
    Test cases for Team Admin role signal handlers.

    Team Admin is a DAB RBAC managed role that should:
    1. Add users to Django Group (for inheritance of team's role assignments)
    2. NOT sync to Pulp RBAC (DAB-only managed role, no Pulp equivalent)
    3. Work correctly with JWT authentication
    """

    def setUp(self):
        """Set up test data."""
        self.org = Organization.objects.create(name="Test Org")
        self.team = Team.objects.create(name="Test Team", organization=self.org)
        self.user = User.objects.create(username="test_user")
        # Create a superuser to test Team Admin role assignment for platform administrators
        self.superuser = User.objects.create(
            username="test_superuser", is_superuser=True, is_staff=True
        )
        self.group = self.team.group

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    def test_team_admin_adds_user_to_group(
        self, mock_dab_signals, mock_signal_in_progress
    ):
        """
        Test that Team Admin role assignment adds user to Django Group.

        This is critical for inheritance - Team Admin should inherit all
        permissions assigned to the team, just like Team Member.

        From DAB managed.py:
        Team Admin: "Can manage a single team and inherits all role assignments to the team"
        """
        from galaxy_ng.app.signals.handlers import copy_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment

        # Disable loop prevention so the handler executes normally
        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Create Team Admin role definition
        role_def = Mock()
        role_def.name = "Team Admin"

        # Create a role assignment representing Team Admin being granted to a user
        assignment = Mock(spec=RoleUserAssignment)
        assignment.role_definition = role_def
        assignment.user = self.user
        assignment.content_object = self.team

        # Verify user not in group initially
        self.assertNotIn(
            self.user,
            self.group.user_set.all(),
            "User should not be in group before Team Admin role assignment"
        )

        # Trigger the signal handler that processes new role assignments
        copy_dab_user_role_assignment(None, assignment, created=True)

        # Team Admin should add user to Django Group to enable role inheritance
        self.assertIn(
            self.user,
            self.group.user_set.all(),
            "Team Admin should add user to Django Group for inheritance"
        )

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    @patch("galaxy_ng.app.signals.handlers.RoleUserAssignment")
    def test_team_admin_removal_keeps_group_if_team_member_exists(
        self, mock_assignment_model, mock_dab_signals, mock_signal_in_progress
    ):
        """
        Test that removing Team Admin keeps user in group if they still have Team Member.

        Scenario: User has both Team Admin and Team Member roles.
        When Team Admin is removed, they should stay in the group
        because Team Member still grants membership.
        """
        from galaxy_ng.app.signals.handlers import delete_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment

        # Disable loop prevention so the handler executes normally
        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Start with user in the group (simulating they have both Team Admin and Team Member)
        self.group.user_set.add(self.user)
        self.assertIn(self.user, self.group.user_set.all())

        # Create Team Admin role definition
        role_def = Mock()
        role_def.name = "Team Admin"

        # Create the Team Admin role assignment that's being removed
        assignment = Mock(spec=RoleUserAssignment)
        assignment.role_definition = role_def
        assignment.user = self.user
        assignment.content_object = self.team
        assignment.object_id = self.team.id

        # Mock that user still has other team roles (e.g., Team Member remains)
        mock_assignment_model.objects.filter.return_value.exists.return_value = True

        # Trigger the delete handler for Team Admin role
        delete_dab_user_role_assignment(None, assignment)

        # User should remain in group because they still have Team Member role
        self.assertIn(
            self.user,
            self.group.user_set.all(),
            "User should stay in group if they still have Team Member or Team Admin"
        )

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    @patch("ansible_base.rbac.models.RoleUserAssignment.objects.filter")
    def test_team_admin_removal_removes_from_group_when_last_role(
        self, mock_filter, mock_dab_signals, mock_signal_in_progress
    ):
        """
        Test that removing Team Admin removes user from group if it's their last team role.

        Scenario: User only has Team Admin (no Team Member).
        When Team Admin is removed, they should be removed from the group.
        """
        from galaxy_ng.app.signals.handlers import delete_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment

        # Disable loop prevention so the handler executes normally
        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Mock that user has NO other team roles (Team Admin is their only team role)
        mock_filter.return_value.exists.return_value = False

        # Start with user in the group (simulating they currently have Team Admin)
        self.group.user_set.add(self.user)
        self.assertIn(self.user, self.group.user_set.all())

        # Create Team Admin role definition
        role_def = Mock()
        role_def.name = "Team Admin"

        # Create the Team Admin role assignment being removed
        assignment = Mock(spec=RoleUserAssignment)
        assignment.role_definition = role_def
        assignment.user = self.user
        assignment.content_object = self.team
        assignment.object_id = self.team.id

        # Trigger the delete handler
        delete_dab_user_role_assignment(None, assignment)

        # User should be removed from group since they have no other team roles
        self.assertNotIn(
            self.user,
            self.group.user_set.all(),
            "User should be removed from group when Team Admin is their last team role"
        )

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    def test_team_admin_vs_team_member_both_add_to_group(
        self, mock_dab_signals, mock_signal_in_progress
    ):
        """
        Test that both Team Admin and Team Member add users to the same group.

        This ensures both roles provide inheritance of team's permissions.
        """
        from galaxy_ng.app.signals.handlers import copy_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment

        team_member_role = "Team Member"
        team_admin_role = "Team Admin"

        # Disable loop prevention so the handler executes normally
        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Create a second user who will get Team Admin role
        team_admin_user = User.objects.create(username="team_admin_user")

        # Assign Team Member to first user and verify they're added to group
        role_def_member = Mock()
        role_def_member.name = team_member_role
        assignment_member = Mock(spec=RoleUserAssignment)
        assignment_member.role_definition = role_def_member
        assignment_member.user = self.user
        assignment_member.content_object = self.team

        copy_dab_user_role_assignment(None, assignment_member, created=True)
        self.assertIn(self.user, self.group.user_set.all())

        # Assign Team Admin to second user and verify they're also added to group
        role_def_admin = Mock()
        role_def_admin.name = team_admin_role
        assignment_admin = Mock(spec=RoleUserAssignment)
        assignment_admin.role_definition = role_def_admin
        assignment_admin.user = team_admin_user
        assignment_admin.content_object = self.team

        copy_dab_user_role_assignment(None, assignment_admin, created=True)
        self.assertIn(team_admin_user, self.group.user_set.all())

        # Verify both users are in the same Django Group for inheritance
        self.assertEqual(
            set(self.group.user_set.all()),
            {self.user, team_admin_user},
            f"Both {team_member_role} and {team_admin_role} should add to the same Django Group"
        )

    def test_team_admin_assignment_to_superuser(self):
        """
        Test Team Admin role assignment to superuser.

        This test verifies that Team Admin roles work correctly when assigned
        to platform administrators (superusers).

        EXPECTED BEHAVIOR:
        - Team Admin is added to Django Group for inheritance
        - Team Admin does NOT sync to Pulp RBAC (DAB-only role)
        - No validation errors occur during assignment
        """
        from galaxy_ng.app.signals.handlers import copy_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment

        with (
            patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress", return_value=False),
            patch("galaxy_ng.app.signals.handlers.dab_rbac_signals") as mock_dab_signals,
        ):
            mock_dab_signals.return_value.__enter__ = Mock()
            mock_dab_signals.return_value.__exit__ = Mock()

            # Create Team Admin assignment for a superuser
            role_def = Mock()
            role_def.name = "Team Admin"

            assignment = Mock(spec=RoleUserAssignment)
            assignment.role_definition = role_def
            assignment.user = self.superuser
            assignment.content_object = self.team
            assignment.object_id = self.team.id

            # Verify Team Admin does NOT attempt Pulp sync
            with patch("galaxy_ng.app.signals.handlers._apply_dab_assignment") as mock_apply:
                copy_dab_user_role_assignment(None, assignment, created=True)

                # ASSERT: Team Admin should NOT sync to Pulp
                mock_apply.assert_not_called()

            # ASSERT: Superuser should be added to Django Group for inheritance
            self.assertIn(
                self.superuser,
                self.group.user_set.all(),
                "Team Admin must add superuser to Group, not sync to Pulp"
            )

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    def test_team_admin_does_not_sync_when_pulp_role_exists(
        self, mock_dab_signals, mock_signal_in_progress
    ):
        """
        Test that Team Admin does not sync to Pulp even when a Pulp Role exists.

        Team Admin is a DAB-only role handled via Django Group membership.
        Even if a Pulp Role named "Team Admin" exists in the database, the signal
        handler should not attempt synchronization.
        """
        from galaxy_ng.app.signals.handlers import copy_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment
        from pulpcore.plugin.models.role import Role
        from django.core.exceptions import BadRequest

        role_name = "Team Admin"

        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Create a Pulp Role that happens to have the same name
        Role.objects.create(
            name=role_name,
            description=f"{role_name} role without Team permissions"
        )

        # Create a DAB role assignment
        role_def = Mock()
        role_def.name = role_name

        assignment = Mock(spec=RoleUserAssignment)
        assignment.role_definition = role_def
        assignment.user = self.user
        assignment.content_object = self.team

        # Signal handler should use Django Groups, not Pulp sync
        copy_dab_user_role_assignment(None, assignment, created=True)

        # Verify user was added to Django Group for role inheritance
        self.assertIn(
            self.user,
            self.group.user_set.all(),
            "Team Admin should add user to group even when Pulp Role exists"
        )

        # Demonstrate that _apply_dab_assignment() would fail if called.
        # This shows why Team Admin must not attempt Pulp synchronization.
        from galaxy_ng.app.signals.handlers import _apply_dab_assignment

        with pytest.raises(BadRequest) as exc_info:
            _apply_dab_assignment(assignment)

        # Confirm the validation error when attempting Pulp synchronization
        assert f"The role '{role_name}' does not carry any permission for that object" in \
            str(exc_info.value)

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.dab_rbac_signals")
    def test_team_admin_does_not_sync_when_pulp_role_missing(
        self, mock_dab_signals, mock_signal_in_progress
    ):
        """
        Test that Team Admin does not attempt Pulp sync when no Pulp Role exists.

        Team Admin is a DAB-only role handled via Django Group membership.
        The signal handler should not attempt to sync to Pulp regardless of whether
        a Pulp Role exists or not.
        """
        from galaxy_ng.app.signals.handlers import copy_dab_user_role_assignment
        from ansible_base.rbac.models import RoleUserAssignment
        from pulpcore.plugin.models.role import Role

        role_name = "Team Admin"

        mock_signal_in_progress.return_value = False
        mock_dab_signals.return_value.__enter__ = Mock()
        mock_dab_signals.return_value.__exit__ = Mock()

        # Verify no Pulp Role named "Team Admin" exists
        self.assertFalse(Role.objects.filter(name=role_name).exists())

        # Create a DAB role assignment
        role_def = Mock()
        role_def.name = role_name

        assignment = Mock(spec=RoleUserAssignment)
        assignment.role_definition = role_def
        assignment.user = self.user
        assignment.content_object = self.team

        # Signal handler should use Django Groups, not attempt Pulp sync
        copy_dab_user_role_assignment(None, assignment, created=True)

        # Verify user was added to Django Group for role inheritance
        self.assertIn(
            self.user,
            self.group.user_set.all(),
            "Team Admin should add user to group without needing Pulp Role"
        )

        # Verify that no Pulp Role was created during the assignment
        self.assertFalse(Role.objects.filter(name=role_name).exists())
