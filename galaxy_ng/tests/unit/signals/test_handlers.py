import pytest
from unittest.mock import Mock, patch


# Mock the Django and external imports at module level to avoid import issues
@pytest.fixture(autouse=True)
def mock_django_imports():
    """Mock Django and external dependencies to allow tests to run."""
    with patch.dict(
        "sys.modules",
        {
            "django.db.models": Mock(),
            "django.db.models.signals": Mock(),
            "django.contrib.auth.models": Mock(),
            "django.contrib.contenttypes.models": Mock(),
            "rest_framework.exceptions": Mock(),
            "pulp_ansible.app.models": Mock(),
            "pulpcore.plugin.models": Mock(),
            "pulpcore.plugin.util": Mock(),
            "ansible_base.rbac.models": Mock(),
            "ansible_base.rbac.validators": Mock(),
            "ansible_base.rbac": Mock(),
        },
    ):
        yield


class TestAnsibleRepositorySignals:
    """Test AnsibleRepository signal handlers."""

    @patch("galaxy_ng.app.signals.handlers.AnsibleRepository")
    def test_ensure_retain_repo_versions_on_repository_created(self, mock_repo_model):
        """Test that retain_repo_versions is set to 1 when repository is created."""
        from galaxy_ng.app.signals.handlers import ensure_retain_repo_versions_on_repository

        mock_instance = Mock()
        mock_instance.retain_repo_versions = None

        ensure_retain_repo_versions_on_repository(
            sender=mock_repo_model, instance=mock_instance, created=True
        )

        assert mock_instance.retain_repo_versions == 1
        mock_instance.save.assert_called_once()

    @patch("galaxy_ng.app.signals.handlers.AnsibleRepository")
    def test_ensure_retain_repo_versions_on_repository_not_created(self, mock_repo_model):
        """Test that retain_repo_versions is not modified when repository is updated."""
        from galaxy_ng.app.signals.handlers import ensure_retain_repo_versions_on_repository

        mock_instance = Mock()
        mock_instance.retain_repo_versions = None

        ensure_retain_repo_versions_on_repository(
            sender=mock_repo_model, instance=mock_instance, created=False
        )

        assert mock_instance.retain_repo_versions is None
        mock_instance.save.assert_not_called()

    @patch("galaxy_ng.app.signals.handlers.AnsibleRepository")
    def test_ensure_retain_repo_versions_on_repository_already_set(self, mock_repo_model):
        """Test that retain_repo_versions is not modified when already set."""
        from galaxy_ng.app.signals.handlers import ensure_retain_repo_versions_on_repository

        mock_instance = Mock()
        mock_instance.retain_repo_versions = 5

        ensure_retain_repo_versions_on_repository(
            sender=mock_repo_model, instance=mock_instance, created=True
        )

        assert mock_instance.retain_repo_versions == 5
        mock_instance.save.assert_not_called()


class TestAnsibleDistributionSignals:
    """Test AnsibleDistribution signal handlers."""

    @patch("galaxy_ng.app.signals.handlers.ContentRedirectContentGuard")
    def test_ensure_content_guard_exists_on_distribution_created(self, mock_guard_model):
        """Test that content guard is set when distribution is created."""
        from galaxy_ng.app.signals.handlers import ensure_content_guard_exists_on_distribution

        mock_content_guard = Mock()
        mock_guard_model.objects.first.return_value = mock_content_guard

        mock_instance = Mock()
        mock_instance.content_guard = None

        ensure_content_guard_exists_on_distribution(
            sender=Mock(), instance=mock_instance, created=True
        )

        assert mock_instance.content_guard == mock_content_guard
        mock_instance.save.assert_called_once()

    @patch("galaxy_ng.app.signals.handlers.ContentRedirectContentGuard")
    def test_ensure_content_guard_exists_on_distribution_not_created(self, mock_guard_model):
        """Test that content guard is not set when distribution is updated."""
        from galaxy_ng.app.signals.handlers import ensure_content_guard_exists_on_distribution

        mock_instance = Mock()
        mock_instance.content_guard = None

        ensure_content_guard_exists_on_distribution(
            sender=Mock(), instance=mock_instance, created=False
        )

        mock_instance.save.assert_not_called()


class TestCollectionSignals:
    """Test Collection signal handlers."""

    @patch("galaxy_ng.app.signals.handlers.Namespace")
    def test_create_namespace_if_not_present(self, mock_namespace_model):
        """Test that namespace is created when collection is saved."""
        from galaxy_ng.app.signals.handlers import create_namespace_if_not_present

        mock_instance = Mock()
        mock_instance.namespace = "test_namespace"

        create_namespace_if_not_present(sender=Mock(), instance=mock_instance, created=True)

        mock_namespace_model.objects.get_or_create.assert_called_once_with(name="test_namespace")

    @patch("galaxy_ng.app.signals.handlers.Namespace")
    def test_associate_namespace_metadata_new_namespace(self, mock_namespace_model):
        """Test namespace metadata association when namespace is new."""
        from galaxy_ng.app.signals.handlers import associate_namespace_metadata

        mock_instance = Mock()
        mock_instance.name = "test_namespace"
        mock_instance.company = "Test Company"
        mock_instance.email = "test@example.com"
        mock_instance.description = "Test Description"
        mock_instance.resources = "Test Resources"
        mock_instance.links = {"github": "https://github.com/test"}
        mock_instance.metadata_sha256 = "sha256hash"

        mock_namespace = Mock()
        mock_namespace.last_created_pulp_metadata = None
        mock_namespace.metadata_sha256 = None
        mock_namespace_model.objects.get_or_create.return_value = (mock_namespace, True)

        associate_namespace_metadata(sender=Mock(), instance=mock_instance, created=True)

        mock_namespace_model.objects.get_or_create.assert_called_once_with(name="test_namespace")
        assert mock_namespace.last_created_pulp_metadata == mock_instance
        mock_namespace.set_links.assert_called_once_with(
            [{"name": "github", "url": "https://github.com/test"}]
        )
        mock_namespace.save.assert_called_once()


class TestRBACUtilityFunctions:
    """Test RBAC utility functions."""

    def test_rbac_context_managers(self):
        """Test RBAC context managers and state management."""
        from galaxy_ng.app.signals.handlers import (
            pulp_rbac_signals,
            dab_rbac_signals,
            rbac_signal_in_progress,
            rbac_state,
        )

        # Reset state
        rbac_state.pulp_action = False
        rbac_state.dab_action = False

        # Test initial state
        assert rbac_signal_in_progress() is False

        # Test pulp_rbac_signals context manager
        with pulp_rbac_signals():
            assert rbac_state.pulp_action is True
            assert rbac_signal_in_progress() is True
        assert rbac_state.pulp_action is False

        # Test dab_rbac_signals context manager
        with dab_rbac_signals():
            assert rbac_state.dab_action is True
            assert rbac_signal_in_progress() is True
        assert rbac_state.dab_action is False

    def test_pulp_role_to_single_content_type_or_none(self):
        """Test pulp_role_to_single_content_type_or_none utility function."""
        from galaxy_ng.app.signals.handlers import pulp_role_to_single_content_type_or_none

        # Test single content type
        mock_content_type = Mock()
        mock_permission1 = Mock(content_type=mock_content_type)
        mock_permission2 = Mock(content_type=mock_content_type)
        mock_role = Mock()
        mock_role.permissions.all.return_value = [mock_permission1, mock_permission2]

        result = pulp_role_to_single_content_type_or_none(mock_role)
        assert result == mock_content_type

        # Test multiple content types
        mock_content_type2 = Mock()
        mock_permission3 = Mock(content_type=mock_content_type2)
        mock_role.permissions.all.return_value = [mock_permission1, mock_permission3]

        result = pulp_role_to_single_content_type_or_none(mock_role)
        assert result is None


class TestRoleDefinitionSignals:
    """Test RoleDefinition signal handlers."""

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.RoleDefinition")
    @patch("galaxy_ng.app.signals.handlers.pulp_role_to_single_content_type_or_none")
    def test_copy_role_to_role_definition(
        self, mock_content_type_func, mock_roledef_model, mock_signal_check
    ):
        """Test copying Pulp Role to DAB RoleDefinition."""
        from galaxy_ng.app.signals.handlers import copy_role_to_role_definition

        mock_signal_check.return_value = False
        mock_content_type_func.return_value = Mock()

        mock_instance = Mock()
        mock_instance.name = "test.role"
        mock_instance.locked = True
        mock_instance.description = "Test Role"

        mock_roledef_model.objects.filter.return_value.first.return_value = None

        copy_role_to_role_definition(sender=Mock(), instance=mock_instance, created=True)

        mock_roledef_model.objects.create.assert_called_once()

    def test_constants_and_mappings(self):
        """Test that constants and role mappings are defined correctly."""
        from galaxy_ng.app.signals.handlers import (
            PULP_TO_ROLEDEF,
            ROLEDEF_TO_PULP,
            SHARED_TEAM_ROLE,
        )

        assert isinstance(PULP_TO_ROLEDEF, dict)
        assert isinstance(ROLEDEF_TO_PULP, dict)
        assert isinstance(SHARED_TEAM_ROLE, str)
        assert SHARED_TEAM_ROLE == "Team Member"


class TestUserRoleSignals:
    """Test UserRole signal handlers."""

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.RoleDefinition")
    def test_copy_pulp_user_role_task_dispatcher(self, mock_roledef_model, mock_signal_check):
        """Test that task dispatcher role is ignored."""
        from galaxy_ng.app.signals.handlers import copy_pulp_user_role

        mock_signal_check.return_value = False

        mock_instance = Mock()
        mock_instance.role.name = "core.task_user_dispatcher"

        result = copy_pulp_user_role(sender=Mock(), instance=mock_instance, created=True)

        # Should return early for task dispatcher role
        assert result is None

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.RoleDefinition")
    def test_copy_pulp_user_role_with_content_object(self, mock_roledef_model, mock_signal_check):
        """Test copying UserRole with content object."""
        from galaxy_ng.app.signals.handlers import copy_pulp_user_role

        mock_signal_check.return_value = False

        mock_instance = Mock()
        mock_instance.role.name = "test.role"
        mock_instance.user = Mock()
        mock_instance.content_object = Mock()

        mock_rd = Mock()
        mock_roledef_model.objects.filter.return_value.first.return_value = mock_rd

        with patch(
            "galaxy_ng.app.signals.handlers.lazy_content_type_correction"
        ) as mock_lazy_correction:
            copy_pulp_user_role(sender=Mock(), instance=mock_instance, created=True)

            mock_lazy_correction.assert_called_once_with(mock_rd, mock_instance.content_object)
            mock_rd.give_permission.assert_called_once_with(
                mock_instance.user, mock_instance.content_object
            )

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.RoleDefinition")
    def test_delete_pulp_user_role(self, mock_roledef_model, mock_signal_check):
        """Test deleting UserRole assignments."""
        from galaxy_ng.app.signals.handlers import delete_pulp_user_role

        mock_signal_check.return_value = False

        mock_instance = Mock()
        mock_instance.role.name = "test.role"
        mock_instance.user = Mock()
        mock_instance.content_object = Mock()

        mock_rd = Mock()
        mock_roledef_model.objects.filter.return_value.first.return_value = mock_rd

        delete_pulp_user_role(sender=Mock(), instance=mock_instance)

        mock_rd.remove_permission.assert_called_once_with(
            mock_instance.user, mock_instance.content_object
        )


class TestDABAssignmentSignals:
    """Test DAB assignment signal handlers."""

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers._apply_dab_assignment")
    def test_copy_dab_user_role_assignment_regular_role(
        self, mock_apply_assignment, mock_signal_check
    ):
        """Test DAB user role assignment for regular role."""
        from galaxy_ng.app.signals.handlers import copy_dab_user_role_assignment

        mock_signal_check.return_value = False

        mock_instance = Mock()
        mock_instance.role_definition.name = "test.role"

        copy_dab_user_role_assignment(sender=Mock(), instance=mock_instance, created=True)

        mock_apply_assignment.assert_called_once_with(mock_instance)

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers._apply_dab_assignment")
    def test_copy_dab_user_role_assignment_shared_team_role(
        self, mock_apply_assignment, mock_signal_check
    ):
        """Test DAB user role assignment for shared team role."""
        from galaxy_ng.app.signals.handlers import (
            copy_dab_user_role_assignment,
            RoleUserAssignment,
            SHARED_TEAM_ROLE,
        )

        mock_signal_check.return_value = False

        mock_instance = Mock(spec=RoleUserAssignment)
        mock_instance.role_definition.name = SHARED_TEAM_ROLE
        mock_instance.user = Mock()
        mock_instance.content_object.group.user_set = Mock()

        copy_dab_user_role_assignment(sender=Mock(), instance=mock_instance, created=True)

        mock_instance.content_object.group.user_set.add.assert_called_once_with(mock_instance.user)
        mock_apply_assignment.assert_not_called()

    @patch("galaxy_ng.app.signals.handlers.Role")
    @patch("galaxy_ng.app.signals.handlers.assign_role")
    def test_apply_dab_assignment(self, mock_assign_role, mock_role_model):
        """Test _apply_dab_assignment helper function."""
        from galaxy_ng.app.signals.handlers import _apply_dab_assignment

        mock_role_model.objects.filter.return_value.exists.return_value = True

        mock_assignment = Mock()
        mock_assignment.role_definition.name = "test.role"
        mock_assignment.user = Mock()
        mock_assignment.object_id = "123"
        mock_assignment.content_object = Mock()

        with patch("galaxy_ng.app.signals.handlers.isinstance") as mock_isinstance:
            mock_isinstance.side_effect = lambda obj, cls: cls.__name__ == "RoleUserAssignment"

            _apply_dab_assignment(mock_assignment)

            mock_assign_role.assert_called_once()


class TestCreateManagedRoles:
    """Test create_managed_roles function."""

    @patch("galaxy_ng.app.signals.handlers.copy_roles_to_role_definitions")
    @patch("galaxy_ng.app.signals.handlers.permission_registry")
    @patch("galaxy_ng.app.signals.handlers.apps")
    def test_create_managed_roles(self, mock_apps, mock_registry, mock_copy_roles):
        """Test create_managed_roles function."""
        from galaxy_ng.app.signals.handlers import create_managed_roles

        with patch("galaxy_ng.app.signals.handlers.dab_rbac_signals") as mock_context:
            mock_context.return_value.__enter__ = Mock()
            mock_context.return_value.__exit__ = Mock()

            create_managed_roles()

            mock_registry.create_managed_roles.assert_called_once_with(mock_apps)
            mock_copy_roles.assert_called_once_with(mock_apps, None)


class TestM2MSignalHandlers:
    """Test many-to-many signal handlers."""

    @patch("galaxy_ng.app.signals.handlers.rbac_signal_in_progress")
    @patch("galaxy_ng.app.signals.handlers.copy_permissions_role_to_role")
    @patch("galaxy_ng.app.signals.handlers.RoleDefinition")
    def test_copy_permission_role_to_rd(
        self, mock_roledef_model, mock_copy_perms, mock_signal_check
    ):
        """Test copy_permission_role_to_rd M2M signal handler."""
        from galaxy_ng.app.signals.handlers import copy_permission_role_to_rd

        mock_signal_check.return_value = False

        mock_instance = Mock()
        mock_instance.name = "test.role"

        mock_rd = Mock()
        mock_roledef_model.objects.filter.return_value.first.return_value = mock_rd

        copy_permission_role_to_rd(
            instance=mock_instance, action="post_add", model=Mock(), pk_set={1, 2}, reverse=False
        )

        mock_copy_perms.assert_called_once_with(mock_instance, mock_rd)

        # Test pre_ actions - should return early
        mock_copy_perms.reset_mock()

        copy_permission_role_to_rd(
            instance=mock_instance, action="pre_add", model=Mock(), pk_set={1, 2}, reverse=False
        )

        mock_copy_perms.assert_not_called()

        # Test reverse relationship - should raise error
        with pytest.raises(
            RuntimeError, match="Removal of permissions through reverse relationship"
        ):
            copy_permission_role_to_rd(
                instance=mock_instance, action="post_add", model=Mock(), pk_set={1, 2}, reverse=True
            )
