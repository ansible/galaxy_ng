
import logging
import pprint

from django.urls import reverse

from rest_framework import status as http_code

from pulp_ansible.app import models as pulp_ansible_models

from galaxy_ng.app.api import permissions
from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app import models as galaxy_models
from galaxy_ng.app.models import auth as auth_models

from .base import BaseTestCase

log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.DEBUG)


class TestUiMySyncListViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(username='admin')
        self.pe_group = auth_models.Group.objects.create(
            name=permissions.IsPartnerEngineer.GROUP_NAME)
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.synclists_url = reverse('galaxy:api:v3:ui:my-synclists-list')
        # self.me_url = reverse('galaxy:api:v3:ui:me')
        self.group1 = auth_models.Group.objects.create(name='test1_group')
        self.user1 = auth_models.User.objects.create_user(username="test1", password="test1-secret")
        self.user1.groups.add(self.group1)
        self.user1.save()
        self.group1.user_set.add(self.user1)
        self.group1.save()

        self.user.groups.add(self.group1)
        self.user.save()
        log.debug('self.user: %s groups: %s', self.user, self.user.groups)
        log.debug('self.user1: %s groups: %s', self.user1, self.user1.groups)
        log.debug('self.group1: %s', self.group1)

    def _create_repository(self, name):
        repo = pulp_ansible_models.AnsibleRepository.objects.create(name='test_repo1')
        return repo

    def _create_synclist(
        self, name, repository, collections=None, namespaces=None,
        policy=None, users=None, groups=None,
    ):
        synclist = galaxy_models.SyncList.objects.create(name=name, repository=repository)
        synclist.groups.set(groups)
        return synclist

    def test_my_synclist_create(self):
        repo = self._create_repository('test_post_repo')
        repo.save()

        synclist_name = 'test_my_synclist_post'
        post_data = {
            'name': synclist_name,
            'repository': repo.pulp_id,
            'collections': [],
            'namespaces': [],
            'policy': 'whitelist',
            'users': [],
            'groups': [],
        }

        self.client.force_authenticate(user=self.user1)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.post(self.synclists_url, post_data, format='json')
            log.debug('response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_201_CREATED)
            log.debug('response.data: %s', response.data)

            self.assertIn('name', response.data)
            self.assertIn('repository', response.data)
            self.assertEqual(response.data['name'], synclist_name)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.post(self.synclists_url, post_data, format='json')
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_my_synclist_update(self):
        repo = self._create_repository('test_post_repo')
        repo.save()
        synclist1 = self._create_synclist(name='test_my_synclist_patch',
                                          repository=repo,
                                          groups=[self.group1])

        synclist1.save()

        ns1_name = "unittestnamespace1"
        ns2_name = "unittestnamespace2"
        ns1 = self._create_namespace(ns1_name, groups=[self.pe_group])
        ns2 = self._create_namespace(ns2_name, groups=[self.pe_group, self.group1])
        ns1.save()
        ns2.save()

        synclist_name = 'test_synclist_patch'
        post_data = {
            'name': synclist_name,
            'repository': repo.pulp_id,
            'collections': [],
            'namespaces': [ns1_name, ns2_name],
            'policy': 'whitelist',
            'users': [self.user1.username],
            'groups': [self.group1.name],
        }

        synclists_detail_url = reverse('galaxy:api:v3:ui:my-synclists-detail',
                                       kwargs={"pk": synclist1.id})
        self.client.force_authenticate(user=self.user1)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.patch(synclists_detail_url, post_data, format='json')
            log.debug('response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_200_OK)
            log.debug('response.data: %s', response.data)

            self.assertIn('name', response.data)
            self.assertIn('repository', response.data)
            self.assertEqual(response.data['name'], synclist_name)
            self.assertEqual(response.data['policy'], "whitelist")
            self.assertIn(self.user1.username, response.data['users'])
            self.assertIn(self.group1.name, response.data['groups'])

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.patch(synclists_detail_url, post_data, format='json')
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_my_synclist_list_no_auth(self):
        self.client.force_authenticate(user=None)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            log.debug('response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_my_synclist_list(self):
        self.client.force_authenticate(user=self.user1)
        repo1 = self._create_repository(name="test_repo1")
        synclist1 = self._create_synclist(name='test_synclist1',
                                          repository=repo1,
                                          groups=[self.group1])

        synclist1.save()

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            data = response.data['data']

            self.assertIsInstance(data, list)
            self.assertEquals(len(data), 1)
            self.assertEquals(data[0]['groups'], [self.group1.name])
            self.assertEquals(data[0]['name'], "test_synclist1")
            self.assertEquals(data[0]['policy'], "blacklist")
            self.assertEquals(data[0]['repository'], repo1.pulp_id)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_my_synclist_list_empty(self):
        self.client.force_authenticate(user=self.user1)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_200_OK)

            data = response.data['data']
            log.debug('response(authed): %s', response)
            log.debug('data: %s', data)

            self.assertEquals(len(data), 0)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_200_OK)

    def test_my_synclist_detail(self):
        self.client.force_authenticate(user=self.user1)
        repo1 = self._create_repository(name="test_repo1")
        synclist_name = 'test_my_synclist_detail'
        synclist1 = self._create_synclist(name=synclist_name,
                                          repository=repo1,
                                          groups=[self.group1],)
        synclist1.save()

        synclists_detail_url = reverse('galaxy:api:v3:ui:my-synclists-detail',
                                       kwargs={"pk": synclist1.id})
        log.debug('synclists_detail_url: %s', synclists_detail_url)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(synclists_detail_url)
            self.assertEqual(response.status_code, http_code.HTTP_200_OK)

            data = response.data
            log.debug('data: %s', pprint.pformat(data))

            self.assertIn('name', response.data)
            self.assertIn('repository', response.data)
            self.assertEqual(response.data['name'], synclist_name)
            self.assertEqual(response.data['policy'], "blacklist")
            self.assertEqual(response.data['collections'], [])
            self.assertEqual(response.data['namespaces'], [])

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(synclists_detail_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_my_synclist_delete(self):
        self.client.force_authenticate(user=self.user1)
        repo1 = self._create_repository(name="test_repo1")
        synclist_name = 'test_synclist_post'
        synclist1 = self._create_synclist(name=synclist_name,
                                          repository=repo1,
                                          groups=[self.group1])
        synclist1.save()
        synclists_detail_url = reverse('galaxy:api:v3:ui:my-synclists-detail',
                                       kwargs={"pk": synclist1.id})
        log.debug('delete url: %s', synclists_detail_url)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.delete(synclists_detail_url)
            log.debug('delete response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.delete(synclists_detail_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)
