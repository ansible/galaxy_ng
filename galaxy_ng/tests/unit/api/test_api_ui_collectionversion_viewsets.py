import urllib

from django.test import override_settings
from django.urls import reverse
from pulp_ansible.app.models import (AnsibleDistribution, AnsibleRepository,
                                     Collection, CollectionVersion)

from galaxy_ng.app import models
from galaxy_ng.app.constants import DeploymentMode
from .base import BaseTestCase


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestUiCollectionVersionViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.versions_url = reverse('galaxy:api:v3:ui:collection-versions-list')
        self.namespace = models.Namespace.objects.create(name='my_namespace')
        self.collection = Collection.objects.create(namespace=self.namespace, name='my_collection')
        self._create_version_in_repo('1.1.1', self._create_repo(name='repo1'))
        self._create_version_in_repo('1.1.2', self._create_repo(name='repo2'))

    @staticmethod
    def _create_repo(name):
        repo = AnsibleRepository.objects.create(name=name)
        AnsibleDistribution.objects.create(name=name, base_path=name, repository=repo)
        return repo

    def _create_version_in_repo(self, version, repo):
        collection_version = CollectionVersion.objects.create(
            namespace=self.namespace,
            collection=self.collection,
            version=version,
        )
        qs = CollectionVersion.objects.filter(pk=collection_version.pk)
        with repo.new_version() as new_version:
            new_version.add_content(qs)

    def _versions_url_with_params(self, query_params):
        return self.versions_url + '?' + urllib.parse.urlencode(query_params)

    def test_no_filters(self):
        response = self.client.get(self.versions_url)
        self.assertEqual(response.data['meta']['count'], 2)

    def test_repo_filter(self):
        url = self._versions_url_with_params({'repository': 'repo_dne'})
        response = self.client.get(url)
        self.assertEqual(response.data['meta']['count'], 0)

        url = self._versions_url_with_params({'repository': 'repo1'})
        response = self.client.get(url)
        self.assertEqual(response.data['meta']['count'], 1)
        self.assertEqual(response.data['data'][0]['version'], '1.1.1')

    def test_multiple_filters(self):
        url = self._versions_url_with_params({
            'namespace': 'namespace_dne',
            'version': '1.1.2',
            'repository': 'repo2',
        })
        response = self.client.get(url)
        self.assertEqual(response.data['meta']['count'], 0)

        url = self._versions_url_with_params({
            'namespace': 'my_namespace',
            'version': '1.1.2',
            'repository': 'repo2',
        })
        response = self.client.get(url)
        self.assertEqual(response.data['meta']['count'], 1)
        self.assertEqual(response.data['data'][0]['version'], '1.1.2')

    def test_sort_and_repo_list(self):
        url = self._versions_url_with_params({'sort': 'pulp_created'})
        response = self.client.get(url)
        self.assertEqual(response.data['data'][0]['version'], '1.1.1')
        self.assertEqual(response.data['data'][0]['repository_list'], ['repo1'])

        url = self._versions_url_with_params({'sort': '-pulp_created'})
        response = self.client.get(url)
        self.assertEqual(response.data['data'][0]['version'], '1.1.2')
        self.assertEqual(response.data['data'][0]['repository_list'], ['repo2'])
