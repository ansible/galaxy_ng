import logging

from django.urls import reverse
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository
from pulpcore.plugin.util import assign_role
from rest_framework import status

from galaxy_ng.app import models
from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import auth as auth_models

from .base import BaseTestCase

log = logging.getLogger(__name__)


class TestV3CollectionUploadOptions(BaseTestCase):
    """
    Regression tests for AAP-89222:

    - Finding #1/#4: OPTIONS to write-only endpoints (e.g. collection upload) must
      not raise ValidationError, or crash with an uncaught DoesNotExist, while
      evaluating permissions against an empty/unresolvable request.
    - Finding #2: the 'POST' entry in OPTIONS metadata (`actions`) must accurately
      reflect whether the user can actually upload -- not just whether they're
      authenticated -- while the outer OPTIONS request itself must still succeed
      (200) for any authenticated user, since this viewset has no other action to
      fall back on.
    """

    deployment_mode = DeploymentMode.STANDALONE.value

    def setUp(self):
        super().setUp()
        self.user_with_upload_perm = auth_models.User.objects.create(username='uploader')
        self.pe_group = self._create_partner_engineer_group()
        self.user_with_upload_perm.groups.add(self.pe_group)
        self.user_with_upload_perm.save()

        self.user_without_perm = auth_models.User.objects.create(username='regular')

        self.user_namespace_owner = auth_models.User.objects.create(username='ns-owner')
        self.owned_namespace = models.Namespace.objects.create(name='ns_owner_namespace')
        self.owned_namespace.users = {
            self.user_namespace_owner: ['galaxy.collection_namespace_owner'],
        }

        # Get or create staging repository and distribution for upload tests
        repo, _ = AnsibleRepository.objects.get_or_create(name='staging')
        AnsibleDistribution.objects.get_or_create(
            name='staging',
            defaults={'base_path': 'staging', 'repository': repo}
        )

    def _options(self, distro_base_path, user):
        upload_url = reverse(
            'galaxy:api:v3:collection-artifact-upload',
            kwargs={'distro_base_path': distro_base_path}
        )
        self.client.force_authenticate(user=user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            return self.client.options(upload_url)

    def test_options_collection_upload_does_not_validate_body(self):
        """
        OPTIONS to collection upload endpoint should return 200 for user with permission,
        NOT 400 ValidationError about missing 'file' field.
        """
        response = self._options('staging', self.user_with_upload_perm)

        # User with upload permission should get 200 OK
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"User with upload permission should get 200 OK, "
            f"got {response.status_code}: {response.data}"
        )

        # Secondary regression check: ensure we never get 400 ValidationError
        self.assertNotEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            f"OPTIONS should not validate body: {response.data}"
        )

        # Verify POST action is included in metadata (CodeRabbit #3898389676)
        # DRF's determine_actions should successfully probe POST permissions
        self.assertIn(
            'POST',
            response.data.get('actions', {}),
            "User with global upload rights should see POST in OPTIONS metadata"
        )

    def test_options_collection_upload_hides_post_without_upload_rights(self):
        """
        AAP-89222 Finding #2: a user with zero upload rights anywhere must not see
        'POST' in OPTIONS metadata, even though the OPTIONS request itself still
        succeeds (200) since this viewset has no other action to fall back on.
        """
        response = self._options('staging', self.user_without_perm)

        # Any authenticated user should still get 200 OK for OPTIONS itself
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Authenticated user should get 200 for OPTIONS, "
            f"got {response.status_code}: {response.data}"
        )

        # Secondary regression check: ensure we never get 400 ValidationError
        self.assertNotEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "OPTIONS should not validate body"
        )

        self.assertNotIn(
            'POST',
            response.data.get('actions', {}),
            "User with no upload rights anywhere should not see POST in metadata"
        )

    def test_options_collection_upload_shows_post_for_namespace_owner(self):
        """
        A user scoped to exactly one namespace (the common non-Partner-Engineer
        ownership pattern) should see 'POST' for a staging-pipeline repo, since
        the approximate check is "can upload to at least one namespace".
        """
        response = self._options('staging', self.user_namespace_owner)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            'POST',
            response.data.get('actions', {}),
            "User who owns a namespace should see POST in OPTIONS metadata"
        )

    def test_options_collection_upload_denied_for_anonymous(self):
        """
        Anonymous users should get 401/403, not 400 ValidationError.
        """
        response = self._options('staging', None)

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
        self.assertNotEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "OPTIONS should not validate body for anonymous users"
        )

    def test_options_collection_upload_unknown_distro_path_does_not_500(self):
        """
        AAP-89222 Finding #1/#4: OPTIONS to an unknown distro_base_path must not
        raise an uncaught DoesNotExist (500). It should deny cleanly instead.
        """
        response = self._options('this-repo-does-not-exist', self.user_with_upload_perm)

        self.assertNotEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"OPTIONS to an unknown path should not 500: {response.data}"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_options_collection_upload_pipeline_none_requires_repo_permission(self):
        """
        For a custom repo with no 'pipeline' label, OPTIONS metadata should reflect
        the exact ansible.modify_ansible_repo_content check the real POST performs,
        not the namespace-based approximation used for staging repos.
        """
        repo = AnsibleRepository.objects.create(name='custom-repo')
        AnsibleDistribution.objects.create(
            name='custom-repo', base_path='custom-repo', repository=repo
        )

        # Owns a namespace, but has no permission on this specific repo.
        response = self._options('custom-repo', self.user_namespace_owner)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(
            'POST',
            response.data.get('actions', {}),
            "Namespace ownership alone should not grant POST on an unlabeled repo"
        )

        # No namespace rights, but has modify permission on this specific repo.
        assign_role('galaxy.ansible_repository_owner', self.user_without_perm, repo)
        response = self._options('custom-repo', self.user_without_perm)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            'POST',
            response.data.get('actions', {}),
            "User with modify_ansible_repo_content on this repo should see POST"
        )

    def test_options_collection_upload_rejected_pipeline_never_shows_post(self):
        """
        A repo whose pipeline is neither 'staging' nor unset (e.g. 'approved') always
        rejects direct uploads, so OPTIONS metadata should never show POST for it --
        regardless of the user's namespace or repo permissions.
        """
        repo = AnsibleRepository.objects.create(
            name='restricted-repo', pulp_labels={"pipeline": "approved"}
        )
        AnsibleDistribution.objects.create(
            name='restricted-repo', base_path='restricted-repo', repository=repo
        )
        assign_role('galaxy.ansible_repository_owner', self.user_with_upload_perm, repo)

        response = self._options('restricted-repo', self.user_with_upload_perm)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(
            'POST',
            response.data.get('actions', {}),
            "A repo with a non-staging pipeline should never advertise POST"
        )
