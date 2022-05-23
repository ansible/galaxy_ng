
import logging

from django.urls import reverse
from pulp_ansible.app.models import AnsibleRepository, AnsibleDistribution
from rest_framework import status

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v3.serializers import NamespaceSerializer
from galaxy_ng.app.constants import DeploymentMode, INBOUND_REPO_NAME_FORMAT

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
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.regular_user = auth_models.User.objects.create(username='regular')

        self.ns_url = reverse('galaxy:api:v3:namespaces-list')

    def test_namespace_validation(self):
        ns_name = "unittestnamespace"
        ns1 = self._create_namespace(ns_name, groups=[self.pe_group])

        ns_detail_url = reverse('galaxy:api:v3:namespaces-detail', kwargs={"name": ns1.name})

        self.client.force_authenticate(user=self.admin_user)

        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            put_data = {
                "name": ns1.name,
                "groups": [],
                "company": "Super duper long name that nobody in their right "
                           "mind should really ever use for a name on anything anywhere.",
                "avatar_url": "not a url",
                "links": [
                    {
                        "name": "link name that is way way too long for anyone",
                        "url": "not a url",
                    },
                    {
                        "name": "link name that is way way too long for anyone",
                        "url": "https://www.valid-url.com/happyface.jpg",
                    }
                ]
            }
            expected_error_fields = {'company', 'avatar_url', 'links__url', 'links__name'}
            expected_error_codes = {'max_length', 'invalid'}

            response = self.client.put(ns_detail_url, put_data, format='json')

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(len(response.data['errors']), 5)

            received_error_fields = set()
            received_error_codes = set()
            for err in response.data['errors']:
                received_error_codes.add(err['code'])
                received_error_fields.add(err['source']['parameter'])

            self.assertEqual(expected_error_codes, received_error_codes)
            self.assertEqual(expected_error_fields, received_error_fields)

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

    def test_related_fields(self):
        self.client.force_authenticate(user=self.admin_user)
        regular_group = self._create_group("users", "regular_users", users=[self.regular_user])

        ns1_name = "unittestnamespace1"
        ns2_name = "unittestnamespace2"
        self._create_namespace(ns1_name, groups=[regular_group])
        self._create_namespace(ns2_name)

        # Test no related fields:
        response = self.client.get(self.ns_url)

        for ns in response.data['data']:
            self.assertEqual(ns['related_fields'], {})

        # Test related fields for admin user
        response = self.client.get(self.ns_url + "?include_related=my_permissions")

        for ns in response.data['data']:
            self.assertIn("my_permissions", ns["related_fields"])
            self.assertGreater(len(ns["related_fields"]["my_permissions"]), 1)

        # Test related fields for non admin user
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.ns_url + "?include_related=my_permissions")

        for ns in response.data['data']:
            self.assertIn("my_permissions", ns["related_fields"])

            if ns["name"] == ns1_name:
                self.assertGreater(len(ns["related_fields"]["my_permissions"]), 1)
            else:
                self.assertEqual(len(ns["related_fields"]["my_permissions"]), 0)

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

    def test_namespace_api_creates_deletes_inbound_repo(self):
        self.client.force_authenticate(user=self.admin_user)
        ns1_name = "unittestnamespace1"
        repo_name = INBOUND_REPO_NAME_FORMAT.format(namespace_name=ns1_name)

        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            # Create namespace + repo
            response = self.client.post(
                self.ns_url,
                {
                    "name": ns1_name,
                    "groups": [
                        {
                            "id": self.pe_group.id,
                            "name": self.pe_group.name,
                            "object_roles": [
                                'galaxy.collection_namespace_owner',
                            ]
                        },
                    ],
                },
                format='json',
            )
            print(f"\n\n response: {response} \n\n")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(1, len(AnsibleRepository.objects.filter(name=repo_name)))
            self.assertEqual(1, len(AnsibleDistribution.objects.filter(name=repo_name)))

            # List namespace
            response = self.client.get(self.ns_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            namespaces = [item['name'] for item in response.data['data']]
            self.assertIn(ns1_name, namespaces)
            self.assertEqual(1, len(Namespace.objects.filter(name=ns1_name)))

            # Delete namespace + repo
            ns_detail_url = reverse('galaxy:api:v3:namespaces-detail', kwargs={"name": ns1_name})
            response = self.client.delete(ns_detail_url)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(0, len(AnsibleRepository.objects.filter(name=repo_name)))
            self.assertEqual(0, len(AnsibleDistribution.objects.filter(name=repo_name)))
            self.assertEqual(0, len(Namespace.objects.filter(name=ns1_name)))

    def test_unauthorized_user_cant_delete_namespace(self):
        ns1_name = "unittestnamespacefordeletion"
        repo_name = INBOUND_REPO_NAME_FORMAT.format(namespace_name=ns1_name)
        self._create_namespace(ns1_name, groups=[self.pe_group])

        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            self.client.force_authenticate(user=self.regular_user)
            ns_detail_url = reverse('galaxy:api:v3:namespaces-detail', kwargs={"name": ns1_name})
            response = self.client.delete(ns_detail_url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(1, len(Namespace.objects.filter(name=ns1_name)))
            self.assertEqual(1, len(AnsibleRepository.objects.filter(name=repo_name)))
            self.assertEqual(1, len(AnsibleDistribution.objects.filter(name=repo_name)))

    def test_delete_namespace_no_error_if_no_repo_exist(self):
        ns2_name = "unittestnamespace2"
        self._create_namespace(ns2_name, groups=[self.pe_group])
        ns_detail_url = reverse('galaxy:api:v3:namespaces-detail', kwargs={"name": ns2_name})
        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.delete(ns_detail_url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_conflict_error_if_already_exists(self):
        """Ensure API returns 409-Conflict in case of existing namespace."""
        ns3_name = "unittestnamespace3"
        self._create_namespace(ns3_name, groups=[self.pe_group])
        ns_list_url = reverse('galaxy:api:v3:namespaces-list')

        self.client.force_authenticate(user=self.admin_user)

        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            post_data = {
                "name": ns3_name,
                "company": "A company name",
                "email": "email@companyname.com",
                "description": "A testing namespace",
                "groups": [
                    {
                        "id": self.pe_group.id,
                        "name": self.pe_group.name,
                        "object_permissions": ["change_namespace", "upload_to_namespace"]
                    }
                ]
            }
            response = self.client.post(ns_list_url, post_data, format='json')
            log.debug('namespace response: %s', response.data)
            self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
