import logging

from django.urls import reverse
from rest_framework import status

from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import auth as auth_models

from .base import BaseTestCase

log = logging.getLogger(__name__)

# /api/automation-hub/v3/namespaces/
# galaxy_ng.app.api.v3.viewsets.namespace.NamespaceViewSet
# galaxy:api:v3:namespaces-list

# /api/automation-hub/v3/namespaces/<name>/
# galaxy_ng.app.api.v3.viewsets.namespace.NamespaceViewSet
# galaxy:api:v3:namespaces-detail


class TestV3NamespaceOptions(BaseTestCase):
    """
    Namespace's "list"/"retrieve" statements allow any authenticated user, so these
    tests focus on: (a) OPTIONS being reachable at all now that the 'metadata' pseudo
    action rides on those statements, and (b) actions.POST/PUT only appearing for
    users who actually hold the underlying create/update permission.
    """

    deployment_mode = DeploymentMode.STANDALONE.value

    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(username='admin')
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.regular_user = auth_models.User.objects.create(username='regular')

        self.ns_url = reverse('galaxy:api:v3:namespaces-list')

    def test_options_denied_for_anonymous_by_default(self):
        self.client.force_authenticate(user=None)
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.options(self.ns_url)
            self.assertIn(
                response.status_code,
                (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
            )

    def test_options_allowed_on_list_for_any_authenticated_user(self):
        self.client.force_authenticate(user=self.regular_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.options(self.ns_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_options_allowed_on_detail_for_any_authenticated_user(self):
        ns1 = self._create_namespace("unittestnamespaceoptions1", groups=[self.pe_group])
        ns_detail_url = reverse('galaxy:api:v3:namespaces-detail', kwargs={"name": ns1.name})

        self.client.force_authenticate(user=self.regular_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.options(ns_detail_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_options_post_action_present_with_add_namespace_perm(self):
        self.client.force_authenticate(user=self.admin_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.options(self.ns_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('POST', response.data.get('actions', {}))

    def test_options_post_action_absent_without_add_namespace_perm(self):
        self.client.force_authenticate(user=self.regular_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.options(self.ns_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotIn('POST', response.data.get('actions', {}))

    def test_options_put_action_present_with_object_level_change_perm(self):
        owning_group = self._create_group(
            "users", "owning_group", users=[self.regular_user]
        )
        ns1 = self._create_namespace("unittestnamespaceoptions2", groups=[owning_group])
        ns_detail_url = reverse('galaxy:api:v3:namespaces-detail', kwargs={"name": ns1.name})

        self.client.force_authenticate(user=self.regular_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.options(ns_detail_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('PUT', response.data.get('actions', {}))

    def test_options_put_action_absent_without_object_level_change_perm(self):
        # regular_user has no group ownership on this namespace, and no
        # model-level change_namespace permission.
        ns1 = self._create_namespace("unittestnamespaceoptions3", groups=[self.pe_group])
        ns_detail_url = reverse('galaxy:api:v3:namespaces-detail', kwargs={"name": ns1.name})

        self.client.force_authenticate(user=self.regular_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.options(ns_detail_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotIn('PUT', response.data.get('actions', {}))

