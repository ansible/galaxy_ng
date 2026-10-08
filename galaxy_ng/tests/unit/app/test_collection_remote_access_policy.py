from unittest import mock

from django.test import override_settings
from pulp_ansible.app.models import AnsibleDistribution

from galaxy_ng.app.access_control.access_policy import CollectionRemoteAccessPolicy
from galaxy_ng.app.access_control.statements.pulp import PULP_VIEWSETS
from galaxy_ng.app.access_control.statements.standalone import STANDALONE_STATEMENTS
from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.tests.unit.api.base import BaseTestCase


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestCollectionRemoteAccessPolicyCanSync(BaseTestCase):
    """Unit tests for CollectionRemoteAccessPolicy.can_sync_collection_remote."""

    def setUp(self):
        super().setUp()
        self.policy = CollectionRemoteAccessPolicy()
        self.modify_perm = "ansible.modify_ansible_repo_content"
        self.request = mock.Mock()
        self.request.user = mock.Mock()
        self.view = mock.Mock()
        self.view.kwargs = {"path": "rh-certified"}

    def test_global_permissions_short_circuit_with_modify(self):
        self.request.user.has_perm.side_effect = lambda perm, obj=None: perm in (
            self.modify_perm,
            "ansible.change_collectionremote",
        )

        result = self.policy.can_sync_collection_remote(
            self.request, self.view, "sync", self.modify_perm
        )

        self.assertTrue(result)

    def test_global_permissions_short_circuit_with_change_repository(self):
        self.request.user.has_perm.side_effect = lambda perm, obj=None: perm in (
            "ansible.change_ansiblerepository",
            "ansible.change_collectionremote",
        )

        result = self.policy.can_sync_collection_remote(
            self.request, self.view, "sync", self.modify_perm
        )

        self.assertTrue(result)

    def test_missing_distribution_path(self):
        self.request.user.has_perm.return_value = False
        self.view.kwargs = {}

        result = self.policy.can_sync_collection_remote(
            self.request, self.view, "sync", self.modify_perm
        )

        self.assertFalse(result)

    def test_requires_both_remote_and_repository_object_perms(self):
        self.request.user.has_perm.return_value = False

        mock_remote = mock.Mock()
        mock_repo = mock.Mock()
        mock_repo.cast.return_value = mock_repo
        mock_distro = mock.Mock()
        mock_distro.repository = mock_repo
        mock_distro.repository.remote.ansible_collectionremote = mock_remote

        with (
            mock.patch.object(AnsibleDistribution.objects, "get", return_value=mock_distro),
            mock.patch(
                "galaxy_ng.app.access_control.access_policy.has_model_or_object_permissions",
                return_value=True,
            ) as mock_object_perm,
        ):
            result = self.policy.can_sync_collection_remote(
                self.request, self.view, "sync", self.modify_perm
            )

        self.assertTrue(result)
        # Repo sync perm is checked first; change_ansiblerepository is skipped when modify succeeds.
        self.assertEqual(mock_object_perm.call_count, 2)
        mock_object_perm.assert_any_call(
            self.request.user, self.modify_perm, mock_repo
        )
        mock_object_perm.assert_any_call(
            self.request.user, "ansible.change_collectionremote", mock_remote
        )

    def test_denied_without_repository_sync_perm(self):
        self.request.user.has_perm.return_value = False

        mock_remote = mock.Mock()
        mock_repo = mock.Mock()
        mock_repo.cast.return_value = mock_repo
        mock_distro = mock.Mock()
        mock_distro.repository = mock_repo
        mock_distro.repository.remote.ansible_collectionremote = mock_remote

        def remote_only_perm(user, perm, obj):
            return perm == "ansible.change_collectionremote" and obj is mock_remote

        with (
            mock.patch.object(AnsibleDistribution.objects, "get", return_value=mock_distro),
            mock.patch(
                "galaxy_ng.app.access_control.access_policy.has_model_or_object_permissions",
                side_effect=remote_only_perm,
            ),
        ):
            result = self.policy.can_sync_collection_remote(
                self.request, self.view, "sync", self.modify_perm
            )

        self.assertFalse(result)

    def test_allowed_with_repository_change_perm_only(self):
        self.request.user.has_perm.return_value = False

        mock_remote = mock.Mock()
        mock_repo = mock.Mock()
        mock_repo.cast.return_value = mock_repo
        mock_distro = mock.Mock()
        mock_distro.repository = mock_repo
        mock_distro.repository.remote.ansible_collectionremote = mock_remote

        with (
            mock.patch.object(AnsibleDistribution.objects, "get", return_value=mock_distro),
            mock.patch(
                "galaxy_ng.app.access_control.access_policy.has_model_or_object_permissions",
                return_value=True,
            ),
        ):
            self.request.user.has_perm.side_effect = (
                lambda perm, obj=None: (
                    perm == "ansible.change_ansiblerepository" and obj is mock_repo
                )
            )

            result = self.policy.can_sync_collection_remote(
                self.request, self.view, "sync", self.modify_perm
            )

        self.assertTrue(result)


class TestCollectionRemoteSyncStatements(BaseTestCase):
    def test_distribution_sync_omits_require_requirements_yaml(self):
        """SyncRemoteView ignores request.data['remote']; keep the shared
        condition on native Pulp repository-sync only."""
        sync = next(
            statement
            for statement in STANDALONE_STATEMENTS["CollectionRemoteViewSet"]
            if statement["action"] == "sync"
        )
        self.assertEqual(
            sync["condition"],
            ["can_sync_collection_remote:ansible.modify_ansible_repo_content"],
        )

        pulp_sync = next(
            statement
            for statement in PULP_VIEWSETS["repositories/ansible/ansible"]["statements"]
            if statement["action"] == ["sync"]
        )
        self.assertIn("require_requirements_yaml", pulp_sync["condition"])
