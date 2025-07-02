"""
Unit tests for team member role signal handlers.

These tests cover the signal handlers that manage the relationship between
DAB RBAC "Team Member" role assignments and Django group membership.
"""

from unittest.mock import Mock, patch

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

    def test_shared_team_role_constant(self):
        """Test that SHARED_TEAM_ROLE constant is set correctly."""
        from galaxy_ng.app.signals.handlers import SHARED_TEAM_ROLE

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
