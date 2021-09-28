import logging
from rest_framework import status
from django.test import override_settings

from galaxy_ng.app.models import auth as auth_models

from galaxy_ng.app.constants import DeploymentMode

from .base import BaseTestCase, get_current_ui_url

log = logging.getLogger(__name__)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestContainerRegistryRemoteViewset(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(username='admin',
                                                          is_superuser=True)
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

    def test_get_registry_list_empty(self):
        url = get_current_ui_url('execution-environments-registry-list')
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.data['data'], [])

    def create_registry_remote(self, name):
        url = get_current_ui_url('execution-environments-registry-list')
        new_registry = {
            'name': name,
            'url' : 'http://example.com',
        }
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(url, new_registry, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data['pk']

    def test_get_detail_with_data(self):
        name = 'my_registry'
        pk = self.create_registry_remote(name)
        url = get_current_ui_url('execution-environments-registry-detail', kwargs={'pk': pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], name)

    def test_get_detail_fail(self):
        pk = 'this key does not exist'
        url = get_current_ui_url('execution-environments-registry-detail', kwargs={'pk': pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_list_with_data(self):
        test_name_1 = 'test_registry_one'
        test_name_2 = 'test_registry_two'
        self.create_registry_remote(test_name_1)
        self.create_registry_remote(test_name_2)
        url = get_current_ui_url('execution-environments-registry-list')
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.data['data'][0]['name'], test_name_1)
        self.assertEqual(response.data['data'][1]['name'], test_name_2)

    def test_update_detail(self):
        initial_name = 'intial_registry_name'
        updated_name = 'updated_registry_name'
        pk = self.create_registry_remote(initial_name)
        url = get_current_ui_url('execution-environments-registry-detail', kwargs={'pk': pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], initial_name)
        # logic for updating the registry
        self.client.put(url, {'name' : updated_name, 'url': 'https://example.com'}, format='json')
        response = self.client.get(url)
        self.assertEqual(response.data['name'], updated_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_detail_fail(self):
        initial_name = 'intial_registry_name'
        updated_name = 'updated_registry_name'
        pk = self.create_registry_remote(initial_name)
        url = get_current_ui_url('execution-environments-registry-detail', kwargs={'pk': pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], initial_name)
        # URL is required in PUT, so this should fail
        response = self.client.put(url, {'name' : updated_name}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_registry_remote(self):
        name = 'registry_to_delete'
        pk = self.create_registry_remote(name)
        url = get_current_ui_url('execution-environments-registry-detail', kwargs={'pk': pk})
        # Get it first
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], name)
        # Delete it
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Get it again
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
