import logging

from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository
from pulpcore.plugin.util import assign_role
from rest_framework import status

from galaxy_ng.app import models
from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import auth as auth_models

from .base import BaseTestCase, get_current_ui_url

log = logging.getLogger(__name__)


class TestCollectionSigningOptions(BaseTestCase):
    """
    Regression tests for AAP-89222:

    - Finding #1/#4: OPTIONS to the collection signing endpoint must not raise
      ValidationError, or crash with an uncaught DoesNotExist, while evaluating
      permissions against an empty/unresolvable request.
    - Finding #3: the 'POST' entry in OPTIONS metadata (`actions`) must accurately
      reflect whether the user can actually sign -- not just whether they're
      authenticated -- while the outer OPTIONS request itself must still succeed
      (200) for any authenticated user, since this view has no other action to
      fall back on.
    """

    deployment_mode = DeploymentMode.STANDALONE.value

    def setUp(self):
        super().setUp()
        self.user_with_sign_perm = auth_models.User.objects.create(username='signer')
        self.user_without_perm = auth_models.User.objects.create(username='regular')

        self.repo, _ = AnsibleRepository.objects.get_or_create(name='sign-test-repo')
        AnsibleDistribution.objects.get_or_create(
            name='sign-test-repo',
            defaults={'base_path': 'sign-test-repo', 'repository': self.repo}
        )
        assign_role('galaxy.ansible_repository_owner', self.user_with_sign_perm, self.repo)

    def _options(self, url, user):
        self.client.force_authenticate(user=user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            return self.client.options(url)

    def test_options_with_repo_permission_shows_post(self):
        """User with modify_ansible_repo_content on the URL-embedded repo sees POST."""
        url = get_current_ui_url('collection-sign-repo', kwargs={'path': 'sign-test-repo'})
        response = self._options(url, self.user_with_sign_perm)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"got {response.status_code}: {response.data}"
        )
        self.assertIn(
            'POST',
            response.data.get('actions', {}),
            "User with modify_ansible_repo_content on this repo should see POST"
        )

    def test_options_without_repo_permission_hides_post(self):
        """
        AAP-89222 Finding #3: a user with no permission on the target repo must not
        see 'POST', even though OPTIONS itself must still succeed (200) since this
        view has no other action to fall back on.
        """
        url = get_current_ui_url('collection-sign-repo', kwargs={'path': 'sign-test-repo'})
        response = self._options(url, self.user_without_perm)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Authenticated user should get 200 for OPTIONS, got {response.status_code}"
        )
        self.assertNotIn(
            'POST',
            response.data.get('actions', {}),
            "User without repo permission should not see POST in OPTIONS metadata"
        )

    def test_options_denied_for_anonymous(self):
        url = get_current_ui_url('collection-sign-repo', kwargs={'path': 'sign-test-repo'})
        response = self._options(url, None)

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_options_unknown_path_does_not_500(self):
        """AAP-89222 Finding #1/#4: an unknown repo path must not crash with a 500."""
        url = get_current_ui_url('collection-sign-repo', kwargs={'path': 'does-not-exist'})
        response = self._options(url, self.user_with_sign_perm)

        self.assertNotEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"OPTIONS to an unknown path should not 500: {response.data}"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_options_bare_endpoint_hides_post_but_stays_200(self):
        """
        The bare /collection_signing/ endpoint has no URL-embedded repo, so the
        target repo can't be resolved during OPTIONS. POST should be hidden, but
        the OPTIONS request itself should still succeed for an authenticated user.
        """
        url = get_current_ui_url('collection-sign')
        response = self._options(url, self.user_with_sign_perm)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"got {response.status_code}: {response.data}"
        )
        self.assertNotIn(
            'POST',
            response.data.get('actions', {}),
            "Bare endpoint can't resolve a target repo, so POST should be hidden"
        )

    def test_options_namespace_kwarg_does_not_gate_metadata(self):
        """
        Carbonite Finding #2: URL-embedded namespace should NOT gate the metadata
        approximation, since the real POST only validates namespace if it comes
        from request.data (which is empty during OPTIONS). A user with repo
        permission but no namespace permission should still see POST.
        """
        # Create a namespace to embed in URL (user has no permission on it)
        models.Namespace.objects.create(name='restricted_ns')

        # URL with both path and namespace kwargs, but user only has repo permission
        url = get_current_ui_url(
            'collection-sign-namespace',
            kwargs={'path': 'sign-test-repo', 'namespace': 'restricted_ns'}
        )
        response = self._options(url, self.user_with_sign_perm)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            'POST',
            response.data.get('actions', {}),
            "User with repo permission should see POST even without namespace permission, "
            "since real POST only checks namespace from request.data (empty here)"
        )
