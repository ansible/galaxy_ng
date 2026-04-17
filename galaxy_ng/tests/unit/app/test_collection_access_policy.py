from unittest import mock

from django.test import override_settings
from pulp_ansible.app.models import AnsibleDistribution

from galaxy_ng.app.access_control.access_policy import CollectionAccessPolicy
from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.tests.unit.api.base import BaseTestCase


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestCollectionAccessPolicyV3CanCopyOrMove(BaseTestCase):
    """Unit tests for CollectionAccessPolicy.v3_can_copy_or_move method."""

    def setUp(self):
        super().setUp()
        self.policy = CollectionAccessPolicy()
        self.permission = "ansible.modify_ansible_repo_content"

        # Create mock request
        self.request = mock.Mock()
        self.request.user = mock.Mock()

        # Create mock view with kwargs
        self.view = mock.Mock()
        self.view.kwargs = {
            "source_path": "staging",
            "dest_path": "published",
        }

    def test_global_permission_short_circuit(self):
        """Test that global permission bypasses object-level check."""
        # User has global permission
        self.request.user.has_perm.return_value = True

        result = self.policy.v3_can_copy_or_move(
            self.request, self.view, "move_content", self.permission
        )

        self.assertTrue(result)
        # Should only check global permission, not call objects.get
        self.request.user.has_perm.assert_called_once_with(self.permission)

    def test_distribution_does_not_exist(self):
        """Test DoesNotExist exception when distribution not found."""
        # User doesn't have global permission
        self.request.user.has_perm.return_value = False

        with mock.patch.object(
            AnsibleDistribution.objects, "get"
        ) as mock_get:
            mock_get.side_effect = AnsibleDistribution.DoesNotExist

            result = self.policy.v3_can_copy_or_move(
                self.request, self.view, "move_content", self.permission
            )

            self.assertFalse(result)

    def test_distribution_has_no_repository(self):
        """Test None repository (distribution exists but .repository is None)."""
        # User doesn't have global permission
        self.request.user.has_perm.return_value = False

        with mock.patch.object(
            AnsibleDistribution.objects, "get"
        ) as mock_get:
            # Mock distribution with None repository
            mock_distribution = mock.Mock()
            mock_distribution.repository = None
            mock_get.return_value = mock_distribution

            result = self.policy.v3_can_copy_or_move(
                self.request, self.view, "move_content", self.permission
            )

            self.assertFalse(result)

    def test_cast_failure_attribute_error(self):
        """Test cast() failure with AttributeError."""
        # User doesn't have global permission
        self.request.user.has_perm.return_value = False

        with mock.patch.object(
            AnsibleDistribution.objects, "get"
        ) as mock_get:
            # Mock repository that raises AttributeError on cast()
            mock_repo = mock.Mock()
            mock_repo.cast.side_effect = AttributeError("cast failed")
            mock_distribution = mock.Mock()
            mock_distribution.repository = mock_repo
            mock_get.return_value = mock_distribution

            result = self.policy.v3_can_copy_or_move(
                self.request, self.view, "move_content", self.permission
            )

            self.assertFalse(result)

    def test_cast_failure_type_error(self):
        """Test cast() failure with TypeError."""
        # User doesn't have global permission
        self.request.user.has_perm.return_value = False

        with mock.patch.object(
            AnsibleDistribution.objects, "get"
        ) as mock_get:
            # Mock repository that raises TypeError on cast()
            mock_repo = mock.Mock()
            mock_repo.cast.side_effect = TypeError("cast type error")
            mock_distribution = mock.Mock()
            mock_distribution.repository = mock_repo
            mock_get.return_value = mock_distribution

            result = self.policy.v3_can_copy_or_move(
                self.request, self.view, "move_content", self.permission
            )

            self.assertFalse(result)

    def test_object_level_permission_both_repos(self):
        """Test success with object-level permissions on both repos."""
        # User doesn't have global permission but has object-level perms
        def has_perm_side_effect(perm, obj=None):
            # Global permission check returns False, object-level returns True
            return obj is not None

        self.request.user.has_perm.side_effect = has_perm_side_effect

        with mock.patch.object(
            AnsibleDistribution.objects, "get"
        ) as mock_get:
            # Mock repositories with successful cast()
            mock_src_repo = mock.Mock()
            mock_src_repo_cast = mock.Mock()
            mock_src_repo.cast.return_value = mock_src_repo_cast

            mock_dest_repo = mock.Mock()
            mock_dest_repo_cast = mock.Mock()
            mock_dest_repo.cast.return_value = mock_dest_repo_cast

            def get_side_effect(base_path):
                mock_distribution = mock.Mock()
                if base_path == "staging":
                    mock_distribution.repository = mock_src_repo
                else:
                    mock_distribution.repository = mock_dest_repo
                return mock_distribution

            mock_get.side_effect = get_side_effect

            result = self.policy.v3_can_copy_or_move(
                self.request, self.view, "move_content", self.permission
            )

            self.assertTrue(result)
            # Verify repos were cached on view
            self.assertEqual(self.view._src_repo, mock_src_repo)
            self.assertEqual(self.view._dest_repo, mock_dest_repo)

    def test_no_permission_on_source_repo(self):
        """Test failure when user doesn't have permission on source repo."""
        # User doesn't have global permission
        def has_perm_side_effect(perm, obj=None):
            # Global permission returns False, only grant on dest repo
            return obj is not None and obj.name == "dest"

        self.request.user.has_perm.side_effect = has_perm_side_effect

        with mock.patch.object(
            AnsibleDistribution.objects, "get"
        ) as mock_get:
            # Mock repositories
            mock_src_repo = mock.Mock()
            mock_src_repo_cast = mock.Mock()
            mock_src_repo_cast.name = "src"
            mock_src_repo.cast.return_value = mock_src_repo_cast

            mock_dest_repo = mock.Mock()
            mock_dest_repo_cast = mock.Mock()
            mock_dest_repo_cast.name = "dest"
            mock_dest_repo.cast.return_value = mock_dest_repo_cast

            def get_side_effect(base_path):
                mock_distribution = mock.Mock()
                if base_path == "staging":
                    mock_distribution.repository = mock_src_repo
                else:
                    mock_distribution.repository = mock_dest_repo
                return mock_distribution

            mock_get.side_effect = get_side_effect

            result = self.policy.v3_can_copy_or_move(
                self.request, self.view, "move_content", self.permission
            )

            self.assertFalse(result)

    def test_no_permission_on_dest_repo(self):
        """Test failure when user doesn't have permission on dest repo."""
        # User doesn't have global permission
        def has_perm_side_effect(perm, obj=None):
            # Global permission returns False, only grant on source repo
            return obj is not None and obj.name == "src"

        self.request.user.has_perm.side_effect = has_perm_side_effect

        with mock.patch.object(
            AnsibleDistribution.objects, "get"
        ) as mock_get:
            # Mock repositories
            mock_src_repo = mock.Mock()
            mock_src_repo_cast = mock.Mock()
            mock_src_repo_cast.name = "src"
            mock_src_repo.cast.return_value = mock_src_repo_cast

            mock_dest_repo = mock.Mock()
            mock_dest_repo_cast = mock.Mock()
            mock_dest_repo_cast.name = "dest"
            mock_dest_repo.cast.return_value = mock_dest_repo_cast

            def get_side_effect(base_path):
                mock_distribution = mock.Mock()
                if base_path == "staging":
                    mock_distribution.repository = mock_src_repo
                else:
                    mock_distribution.repository = mock_dest_repo
                return mock_distribution

            mock_get.side_effect = get_side_effect

            result = self.policy.v3_can_copy_or_move(
                self.request, self.view, "move_content", self.permission
            )

            self.assertFalse(result)
