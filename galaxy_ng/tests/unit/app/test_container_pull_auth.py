"""Tests for the authenticated execution environment pull policy.

The registry token service reads the ``distributions/container/container``
access policy from the database, so these tests exercise both the startup
patch that feeds ``post_migrate`` and the token authorization decision itself.
"""

from copy import deepcopy
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, TestCase, override_settings

from pulp_container.app import models as container_models
from pulp_container.app.authorization import AuthorizationService
from pulp_container.app.registry_api import BearerTokenView
from pulp_container.app.viewsets import ContainerDistributionViewSet
from pulpcore.plugin.models import AccessPolicy

from galaxy_ng.app import require_auth_for_container_pull
from galaxy_ng.app.auth.registry import (
    BasicOrTokenPasswordAuthentication,
    enable_registry_token_password_auth,
)
from galaxy_ng.app.models.auth import User
from galaxy_ng.app.signals.handlers import dab_rbac_signals, pulp_rbac_signals


UPSTREAM_POLICY = {
    "statements": [
        {
            "action": ["pull"],
            "principal": "*",
            "effect": "allow",
            "condition_expression": ["not is_private"],
        },
        {
            "action": ["pull"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_namespace_or_obj_perms:container.pull_containerdistribution"],
        },
        {
            "action": ["push"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_namespace_or_obj_perms:container.push_containerdistribution"],
        },
    ],
    "creation_hooks": [
        {
            "function": "add_roles_for_object_creator",
            "parameters": {"roles": "container.containerdistribution_owner"},
        },
    ],
}


class TestContainerPullPolicyPatch(SimpleTestCase):
    def setUp(self):
        self.original_policy = deepcopy(ContainerDistributionViewSet.DEFAULT_ACCESS_POLICY)
        self.addCleanup(
            setattr,
            ContainerDistributionViewSet,
            "DEFAULT_ACCESS_POLICY",
            self.original_policy,
        )
        ContainerDistributionViewSet.DEFAULT_ACCESS_POLICY = deepcopy(UPSTREAM_POLICY)

    def _pull_statements(self):
        return [
            statement
            for statement in ContainerDistributionViewSet.DEFAULT_ACCESS_POLICY["statements"]
            if "pull" in statement["action"]
        ]

    @override_settings(GALAXY_ENABLE_UNAUTHENTICATED_EE_PULL=False)
    def test_anonymous_pull_statement_requires_authentication(self):
        require_auth_for_container_pull()

        self.assertFalse(
            any(statement["principal"] == "*" for statement in self._pull_statements())
        )
        self.assertTrue(
            any(
                statement["principal"] == "authenticated"
                and "not is_private" in statement.get("condition_expression", [])
                for statement in self._pull_statements()
            )
        )

    @override_settings(GALAXY_ENABLE_UNAUTHENTICATED_EE_PULL=False)
    def test_non_pull_statements_and_creation_hooks_are_preserved(self):
        require_auth_for_container_pull()

        statements = ContainerDistributionViewSet.DEFAULT_ACCESS_POLICY["statements"]
        push_statements = [
            statement for statement in statements if "push" in statement["action"]
        ]
        self.assertEqual(push_statements, UPSTREAM_POLICY["statements"][2:])
        self.assertEqual(
            ContainerDistributionViewSet.DEFAULT_ACCESS_POLICY["creation_hooks"],
            UPSTREAM_POLICY["creation_hooks"],
        )

    @override_settings(GALAXY_ENABLE_UNAUTHENTICATED_EE_PULL=False)
    def test_patch_is_idempotent(self):
        require_auth_for_container_pull()
        first_result = deepcopy(ContainerDistributionViewSet.DEFAULT_ACCESS_POLICY)

        require_auth_for_container_pull()

        self.assertEqual(
            ContainerDistributionViewSet.DEFAULT_ACCESS_POLICY,
            first_result,
        )

    @override_settings(GALAXY_ENABLE_UNAUTHENTICATED_EE_PULL=True)
    def test_opt_out_keeps_anonymous_pull(self):
        require_auth_for_container_pull()

        self.assertTrue(
            any(statement["principal"] == "*" for statement in self._pull_statements())
        )


class TestBasicOrTokenPasswordAuthentication(SimpleTestCase):
    @mock.patch("galaxy_ng.app.auth.registry.authenticate")
    def test_password_authentication_wins(self, authenticate):
        user = mock.Mock()
        authenticate.return_value = user

        result = BasicOrTokenPasswordAuthentication().authenticate_credentials(
            "alice", "correct-password"
        )

        self.assertEqual(result, (user, None))
        authenticate.assert_called_once_with(
            request=None, username="alice", password="correct-password"
        )

    @mock.patch("galaxy_ng.app.auth.registry.Token")
    @mock.patch("galaxy_ng.app.auth.registry.authenticate", return_value=None)
    def test_token_in_password_field_is_accepted(self, authenticate, token_model):
        user = mock.Mock(is_active=True)
        user.get_username.return_value = "alice"
        token = mock.Mock(user=user)
        token_model.objects.select_related.return_value.filter.return_value.first.return_value = (
            token
        )

        result = BasicOrTokenPasswordAuthentication().authenticate_credentials(
            "alice", "api-token"
        )

        self.assertEqual(result, (user, token))
        token_model.objects.select_related.return_value.filter.assert_called_once_with(
            key="api-token"
        )

    @mock.patch("galaxy_ng.app.auth.registry.Token")
    @mock.patch("galaxy_ng.app.auth.registry.authenticate", return_value=None)
    def test_token_belonging_to_another_user_is_rejected(self, authenticate, token_model):
        user = mock.Mock(is_active=True)
        user.get_username.return_value = "bob"
        token = mock.Mock(user=user)
        token_model.objects.select_related.return_value.filter.return_value.first.return_value = (
            token
        )

        result = BasicOrTokenPasswordAuthentication().authenticate_credentials(
            "alice", "api-token"
        )

        self.assertIsNone(result)

    @mock.patch("galaxy_ng.app.auth.registry.Token")
    @mock.patch("galaxy_ng.app.auth.registry.authenticate", return_value=None)
    def test_inactive_token_owner_is_rejected(self, authenticate, token_model):
        user = mock.Mock(is_active=False)
        user.get_username.return_value = "alice"
        token = mock.Mock(user=user)
        token_model.objects.select_related.return_value.filter.return_value.first.return_value = (
            token
        )

        result = BasicOrTokenPasswordAuthentication().authenticate_credentials(
            "alice", "api-token"
        )

        self.assertIsNone(result)

    @mock.patch("galaxy_ng.app.auth.registry.Token")
    @mock.patch("galaxy_ng.app.auth.registry.authenticate", return_value=None)
    def test_unknown_credentials_return_none(self, authenticate, token_model):
        token_model.objects.select_related.return_value.filter.return_value.first.return_value = (
            None
        )

        result = BasicOrTokenPasswordAuthentication().authenticate_credentials(
            "alice", "wrong"
        )

        self.assertIsNone(result)


class TestBearerTokenViewAuthenticationPatch:
    def test_token_password_authenticator_is_prepended(self, monkeypatch):
        monkeypatch.setattr(
            BearerTokenView, "authentication_classes", ["existing-authenticator"]
        )

        enable_registry_token_password_auth()

        assert BearerTokenView.authentication_classes == [
            BasicOrTokenPasswordAuthentication,
            "existing-authenticator",
        ]

    def test_patch_is_idempotent(self, monkeypatch):
        monkeypatch.setattr(
            BearerTokenView, "authentication_classes", ["existing-authenticator"]
        )

        enable_registry_token_password_auth()
        enable_registry_token_password_auth()

        assert BearerTokenView.authentication_classes == [
            BasicOrTokenPasswordAuthentication,
            "existing-authenticator",
        ]


class TestRegistryPullAuthorization(TestCase):
    def setUp(self):
        with mock.patch(
            "pulpcore.app.models.access_policy.AutoAddObjPermsMixin.add_perms"
        ), pulp_rbac_signals(), dab_rbac_signals():
            self.namespace = container_models.ContainerNamespace.objects.create(name="pulltest")
            self.repository = container_models.ContainerPushRepository.objects.create(
                name="pulltest/repo"
            )
            self.distribution = container_models.ContainerDistribution.objects.create(
                name="pulltest/repo",
                base_path="pulltest/repo",
                repository=self.repository,
                namespace=self.namespace,
                private=False,
            )
        self.addCleanup(self._clear_permission_cache)

    def _clear_permission_cache(self):
        for user in User.objects.all():
            user._perm_cache = {}

    def _pull_actions(self, user, private=False):
        container_models.ContainerDistribution.objects.filter(
            pk=self.distribution.pk
        ).update(private=private)
        service = AuthorizationService(
            user,
            "registry.example.com",
            ["repository:pulltest/repo:pull"],
        )
        return service.determine_access()[0]["actions"]

    def test_database_policy_has_no_anonymous_pull(self):
        access_policy = AccessPolicy.objects.get(
            viewset_name="distributions/container/container"
        )
        anonymous_pulls = [
            statement
            for statement in access_policy.statements
            if "pull" in statement.get("action", [])
            and statement.get("principal") == "*"
        ]
        self.assertEqual(anonymous_pulls, [])

    def test_anonymous_user_cannot_pull_public_ee(self):
        self.assertEqual(self._pull_actions(AnonymousUser()), [])

    def test_authenticated_user_can_pull_public_ee(self):
        user = User.objects.create(username="pulluser")
        self.assertEqual(self._pull_actions(user), ["pull"])

    def test_anonymous_user_cannot_pull_private_ee(self):
        self.assertEqual(self._pull_actions(AnonymousUser(), private=True), [])

    def test_superuser_can_pull_private_ee(self):
        user = User.objects.create(username="pulladmin", is_superuser=True, is_staff=True)
        self.assertEqual(self._pull_actions(user, private=True), ["pull"])
