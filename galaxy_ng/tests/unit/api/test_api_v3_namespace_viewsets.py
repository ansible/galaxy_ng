
import logging

from django.urls import reverse

from rest_framework import status

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api import permissions
from galaxy_ng.app.api.v3.serializers import NamespaceSerializer
from galaxy_ng.app.constants import DeploymentMode

from .base import BaseTestCase

log = logging.getLogger(__name__)

# /api/automation-hub/v3/namespaces/
# galaxy_ng.app.api.v3.viewsets.namespace.NamespaceViewSet
# galaxy:api:v3:namespaces-list

# /api/automation-hub/v3/namespaces/<name>/
# galaxy_ng.app.api.v3.viewsets.namespace.NamespaceViewSet
# galaxy:api:v3:namespaces-detail


class TestV3NamespaceViewSet(BaseTestCase):
    deployment_mode = DeploymentMode.STANDALONE.value

    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(username='admin')
        self.pe_group = auth_models.Group.objects.create(
            name=permissions.IsPartnerEngineer.GROUP_NAME)
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.ns_url = reverse('galaxy:api:v3:namespaces-list')

    def test_namespace_list_empty(self):
        self.client.force_authenticate(user=self.admin_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.get(self.ns_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data['data']
            log.debug("data: %s", data)
            self.assertEqual(len(data), Namespace.objects.all().count())

    def test_namespace_list(self):
        self.client.force_authenticate(user=self.admin_user)
        ns1_name = "unittestnamespace1"
        ns2_name = "unittestnamespace2"
        self._create_namespace(ns1_name, groups=[self.pe_group])
        self._create_namespace(ns2_name, groups=[self.pe_group])
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.get(self.ns_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data['data']
            log.debug("data: %s", data)
            self.assertEqual(len(data), Namespace.objects.all().count())

    def test_namespace_get(self):
        ns_name = "unittestnamespace"
        ns1 = self._create_namespace(ns_name, groups=[self.pe_group])

        ns_detail_url = reverse('galaxy:api:v3:namespaces-detail', kwargs={"name": ns1.name})

        self.client.force_authenticate(user=self.admin_user)

        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.get(ns_detail_url)
            log.debug('response: %s', response)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.data
            log.debug('data: %s', data)

            namespace = NamespaceSerializer(data=data)
            log.debug('repr namespace serializer: %r', namespace)

            namespace.is_valid()
            log.debug('namespace.errors: %s', namespace.errors)

            log.debug('namespace.validated_data: %s', namespace.validated_data)

            self.assertEqual(data['name'], ns_name)
            self.assertEqual(data['name'], ns1.name)

            self.assertEqual(data["links"], [])
            self.assertIn("avatar_url", data)
            self.assertIn("company", data)
            self.assertIn("description", data)

            self.assertEqual(len(data['groups']), self.admin_user.groups.all().count())
