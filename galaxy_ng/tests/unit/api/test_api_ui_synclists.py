import logging

from django.urls import reverse

from rest_framework import status as http_code

from galaxy_ng.app.constants import DeploymentMode

from .synclist_base import BaseSyncListViewSet

log = logging.getLogger(__name__)


class TestUiSynclistViewSet(BaseSyncListViewSet):
    url_name = 'galaxy:api:v3:ui:synclists-list'

    def test_synclist_create_as_user(self):
        repo = self._create_repository('test_post_repo')
        repo.save()

        post_data = {
            'repository': repo.pulp_id,
            'collections': [],
            'namespaces': [],
            'policy': 'include',
            'users': [],
            'groups': [],
        }

        self.client.force_authenticate(user=self.user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.post(self.synclists_url, post_data, format='json')
            log.debug('response: %s', response)
            log.debug('response.data: %s', response.data)

            # should fail with auth now
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.post(self.synclists_url, post_data, format='json')
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    # def test_synclist_create_as_pe_group(self):
    #     repo = self._create_repository('test_post_repo')
    #     repo.save()

    #     post_data = {
    #         'repository': repo.pulp_id,
    #         'collections': [],
    #         'namespaces': [],
    #         'policy': 'include',
    #         'users': [],
    #         'groups': [],
    #     }

    #     self.client.force_authenticate(user=self.admin_user)
    #     with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
    #         response = self.client.post(self.synclists_url, post_data, format='json')
    #         log.debug('response: %s', response)

    #         # should fail with auth now
    #         self.assertEqual(response.status_code, http_code.HTTP_201_CREATED)
    #         log.debug('response.data: %s', response.data)

    #         self.assertIn('name', response.data)
    #         self.assertIn('repository', response.data)
    #         self.assertEqual(response.data['name'], 'test_post_repo-synclist')

    #     with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
    #         response = self.client.post(self.synclists_url, post_data, format='json')
    #         self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_update_as_pe_group_user(self):
        repo = self._create_repository('test_post_repo')
        repo.save()
        synclist_name = 'test_synclist_patch'
        synclist1 = self._create_synclist(name=synclist_name,
                                          repository=repo,
                                          upstream_repository=self.default_repo)

        synclist1.save()

        ns1_name = "unittestnamespace1"
        ns2_name = "unittestnamespace2"
        ns1 = self._create_namespace(ns1_name, groups=[self.pe_group])
        ns2 = self._create_namespace(ns2_name, groups=[self.pe_group])
        ns1.save()
        ns2.save()

        post_data = {
            'repository': repo.pulp_id,
            'collections': [],
            'namespaces': [ns1_name, ns2_name],
            'policy': 'include',
            'users': [self.admin_user.username],
            'groups': [self.pe_group.name],
        }

        synclists_detail_url = reverse('galaxy:api:v3:ui:synclists-detail',
                                       kwargs={"pk": synclist1.id})
        self.client.force_authenticate(user=self.admin_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            # should fail with auth now
            response = self.client.patch(synclists_detail_url, post_data, format='json')
            log.debug('response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_200_OK)
            log.debug('response.data: %s', response.data)

            self.assertIn('name', response.data)
            self.assertIn('repository', response.data)
            self.assertEqual(response.data['name'], synclist_name)
            self.assertEqual(response.data['policy'], "include")
            self.assertIn(self.admin_user.username, response.data['users'])
            self.assertIn(self.pe_group.name, response.data['groups'])

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.patch(synclists_detail_url, post_data, format='json')
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_update_as_non_pe_group_user(self):
        repo = self._create_repository('test_post_repo')
        repo.save()
        synclist1 = self._create_synclist(name='test_synclist_patch',
                                          repository=repo,
                                          upstream_repository=self.default_repo)

        synclist1.save()

        ns1_name = "unittestnamespace1"
        ns2_name = "unittestnamespace2"
        ns1 = self._create_namespace(ns1_name, groups=[self.pe_group])
        ns2 = self._create_namespace(ns2_name, groups=[self.pe_group])
        ns1.save()
        ns2.save()

        post_data = {
            'repository': repo.pulp_id,
            'collections': [],
            'namespaces': [ns1_name, ns2_name],
            'policy': 'include',
            'users': [self.user1.username],
            'groups': [self.group1.name],
        }

        synclists_detail_url = reverse('galaxy:api:v3:ui:synclists-detail',
                                       kwargs={"pk": synclist1.id})
        self.client.force_authenticate(user=self.user1)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            # should fail with auth now
            response = self.client.patch(synclists_detail_url, post_data, format='json')
            log.debug('response: %s', response)

            log.debug('response.data: %s', response.data)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.patch(synclists_detail_url, post_data, format='json')
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_list_as_non_pe_group_user(self):
        self.client.force_authenticate(user=self.user1)
        repo1 = self._create_repository(name="test_repo1")
        synclist1 = self._create_synclist(name='test_synclist1',
                                          repository=repo1)

        synclist1.save()

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            log.debug('response.data: %s', response.data)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_list_as_pe_group_user(self):
        self.client.force_authenticate(user=self.admin_user)
        repo1 = self._create_repository(name="test_repo1")
        synclist1 = self._create_synclist(name='test_synclist1',
                                          repository=repo1)

        synclist1.save()

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            log.debug('response.data: %s', response.data)
            self.assertEqual(response.status_code, http_code.HTTP_200_OK)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_list_empty(self):
        # self.client.force_authenticate(user=self.user)

        self.client.force_authenticate(user=self.admin_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_200_OK)
            data = response.data['data']
            # self.assertEqual(len(data), auth_models.User.objects.all().count())
            log.debug('response(authed): %s', response)
            log.debug('data: %s', data)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_200_OK)
            log.debug('response(insights): %s', response)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_detail_as_pe_group_user(self):
        self.client.force_authenticate(user=self.admin_user)
        repo1 = self._create_repository(name="test_repo1")
        synclist_name = "pe_group-synclist"
        synclist1 = self._create_synclist(name=synclist_name, repository=repo1)
        synclist1.save()
        synclists_detail_url = reverse('galaxy:api:v3:ui:synclists-detail',
                                       kwargs={"pk": synclist1.id})

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(synclists_detail_url)

            self.assertEqual(response.status_code, http_code.HTTP_200_OK)
            log.debug('response.data: %s', response.data)

            data = response.data
            import pprint
            log.debug('data: %s', pprint.pformat(data))

            self.assertIn('name', response.data)
            self.assertIn('repository', response.data)
            self.assertEqual(response.data['name'], synclist_name)
            self.assertEqual(response.data['policy'], "exclude")
            self.assertEqual(response.data['collections'], [])
            self.assertEqual(response.data['namespaces'], [])

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(synclists_detail_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_detail_as_non_pe_group_user(self):
        self.client.force_authenticate(user=self.user1)
        repo1 = self._create_repository(name="test_repo1")
        synclist_name = 'test_synclist_post'
        synclist1 = self._create_synclist(name=synclist_name,
                                          repository=repo1)
        synclist1.save()

        synclists_detail_url = reverse('galaxy:api:v3:ui:synclists-detail',
                                       kwargs={"pk": synclist1.id})

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(synclists_detail_url)
            log.debug('response.data: %s', response.data)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(synclists_detail_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_delete_as_pe_group_user(self):
        self.client.force_authenticate(user=self.admin_user)
        repo1 = self._create_repository(name="test_repo1")
        synclist_name = 'test_synclist_post'
        synclist1 = self._create_synclist(name=synclist_name,
                                          repository=repo1)
        synclist1.save()
        synclists_detail_url = reverse('galaxy:api:v3:ui:synclists-detail',
                                       kwargs={"pk": synclist1.id})

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            log.debug('delete url: %s', synclists_detail_url)

            response = self.client.delete(synclists_detail_url)
            log.debug('delete response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.delete(synclists_detail_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_delete_as_non_pe_group_user(self):
        self.client.force_authenticate(user=self.user1)
        repo1 = self._create_repository(name="test_repo1")
        synclist_name = 'test_synclist_post'
        synclist1 = self._create_synclist(name=synclist_name,
                                          repository=repo1)
        synclist1.save()
        synclists_detail_url = reverse('galaxy:api:v3:ui:synclists-detail',
                                       kwargs={"pk": synclist1.id})

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            log.debug('delete url: %s', synclists_detail_url)

            response = self.client.delete(synclists_detail_url)
            log.debug('delete response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.delete(synclists_detail_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)
