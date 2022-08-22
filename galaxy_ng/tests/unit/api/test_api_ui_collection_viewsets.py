import urllib

from django.test import override_settings
from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    Collection,
    CollectionVersion,
    CollectionRemote
)
from galaxy_ng.app import models
from galaxy_ng.app.constants import DeploymentMode
from .base import BaseTestCase, get_current_ui_url


def _create_repo(name, **kwargs):
    repo = AnsibleRepository.objects.create(name=name, **kwargs)
    AnsibleDistribution.objects.create(name=name, base_path=name, repository=repo)
    return repo


def _create_remote(name, url, **kwargs):
    return CollectionRemote.objects.create(
        name=name, url=url, **kwargs
    )


def _get_create_version_in_repo(namespace, collection, repo, **kwargs):
    collection_version, _ = CollectionVersion.objects.get_or_create(
        namespace=namespace,
        name=collection.name,
        collection=collection,
        **kwargs,
    )
    qs = CollectionVersion.objects.filter(pk=collection_version.pk)
    with repo.new_version() as new_version:
        new_version.add_content(qs)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestUiCollectionVersionDependencyFilter(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.versions_url = get_current_ui_url("collection-versions-list")
        self.repo = _create_repo(name="the_repo")
        self.namespace = models.Namespace.objects.create(name="my_namespace")
        collection_foo = Collection.objects.create(namespace=self.namespace, name="foo")
        collection_bar = Collection.objects.create(namespace=self.namespace, name="bar")

        _get_create_version_in_repo(self.namespace, collection_foo, self.repo, version="1.0.0")
        _get_create_version_in_repo(self.namespace, collection_bar, self.repo, version="1.0.0")
        _get_create_version_in_repo(
            self.namespace,
            collection_foo,
            self.repo,
            version="2.0.0",
            dependencies={"my_namespace.bar": "*"},
        )

    def _versions_url_with_params(self, query_params):
        return self.versions_url + "?" + urllib.parse.urlencode(query_params)

    def test_no_filters(self):
        response = self.client.get(self.versions_url)
        self.assertEqual(response.data["meta"]["count"], 3)

    def test_filter_dne(self):
        url = self._versions_url_with_params({"dependency": "ns_dne:name_dne"})
        response = self.client.get(url)
        self.assertEqual(response.data["meta"]["count"], 0)

    def test_filter_match(self):
        url = self._versions_url_with_params({"dependency": "my_namespace.bar"})
        response = self.client.get(url)
        self.assertEqual(response.data["meta"]["count"], 1)
        self.assertEqual(response.data["data"][0]["name"], "foo")
        self.assertEqual(response.data["data"][0]["version"], "2.0.0")

    def test_that_filter_ignores_dependency_version(self):
        collection_baz = Collection.objects.create(namespace=self.namespace, name="baz")
        _get_create_version_in_repo(
            self.namespace,
            collection_baz,
            self.repo,
            version="0.0.1",
            dependencies={"my_namespace.foo": "*"},
        )
        _get_create_version_in_repo(
            self.namespace,
            collection_baz,
            self.repo,
            version="0.0.2",
            dependencies={"my_namespace.foo": "1.0.0"},
        )
        _get_create_version_in_repo(
            self.namespace,
            collection_baz,
            self.repo,
            version="0.0.3",
            dependencies={"my_namespace.foo": ">=2.0.0"},
        )
        _get_create_version_in_repo(
            self.namespace,
            collection_baz,
            self.repo,
            version="0.0.4",
            dependencies={"my_namespace.foo": "9.9.9"},
        )

        url = self._versions_url_with_params({"dependency": "my_namespace.foo"})
        response = self.client.get(url)
        self.assertEqual(response.data["meta"]["count"], 4)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestUiCollectionVersionViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.versions_url = get_current_ui_url('collection-versions-list')
        self.namespace = models.Namespace.objects.create(name='my_namespace')
        self.collection = Collection.objects.create(namespace=self.namespace, name='my_collection')

        _get_create_version_in_repo(
            self.namespace, self.collection, _create_repo(name="repo1"), version="1.1.1"
        )
        _get_create_version_in_repo(
            self.namespace, self.collection, _create_repo(name="repo2"), version="1.1.2"
        )

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


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestUiCollectionViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        namespace_name = 'my_namespace'
        collection1_name = 'collection1'
        collection2_name = 'collection2'

        self.repo1 = _create_repo(name='repo1')
        self.repo2 = _create_repo(name='repo2')
        self.repo3 = _create_repo(name='repo3')
        self.namespace = models.Namespace.objects.create(name=namespace_name)
        self.collection1 = Collection.objects.create(
            namespace=self.namespace, name=collection1_name)
        self.collection2 = Collection.objects.create(
            namespace=self.namespace, name=collection2_name)

        _get_create_version_in_repo(self.namespace, self.collection1, self.repo1, version="1.0.0")
        _get_create_version_in_repo(self.namespace, self.collection1, self.repo1, version="1.0.1")
        _get_create_version_in_repo(self.namespace, self.collection2, self.repo1, version="2.0.0")
        _get_create_version_in_repo(self.namespace, self.collection1, self.repo2, version="1.0.0")

        self.repo1_list_url = get_current_ui_url(
            'collections-list', kwargs={'distro_base_path': 'repo1'})
        self.repo2_list_url = get_current_ui_url(
            'collections-list', kwargs={'distro_base_path': 'repo2'})
        self.repo3_list_url = get_current_ui_url(
            'collections-list', kwargs={'distro_base_path': 'repo3'})
        self.repo1_collection1_detail_url = get_current_ui_url(
            'collections-detail',
            kwargs={
                'distro_base_path': 'repo1',
                'namespace': namespace_name,
                'name': collection1_name})

    def test_list_count(self):
        response = self.client.get(self.repo1_list_url)
        self.assertEqual(response.data['meta']['count'], 2)

        response = self.client.get(self.repo2_list_url)
        self.assertEqual(response.data['meta']['count'], 1)

        response = self.client.get(self.repo3_list_url)
        self.assertEqual(response.data['meta']['count'], 0)

    def test_list_latest_version(self):
        response = self.client.get(self.repo1_list_url)
        c1 = next(i for i in response.data['data'] if i['name'] == self.collection1.name)
        self.assertEqual(c1['latest_version']['version'], '1.0.1')

        c2 = next(i for i in response.data['data'] if i['name'] == self.collection2.name)
        self.assertEqual(c2['latest_version']['version'], '2.0.0')

        response = self.client.get(self.repo2_list_url)
        c1 = next(i for i in response.data['data'] if i['name'] == self.collection1.name)
        self.assertEqual(c1['latest_version']['version'], '1.0.0')

    def test_detail_latest_version(self):
        response = self.client.get(self.repo1_collection1_detail_url)
        self.assertEqual(response.data['latest_version']['version'], '1.0.1')

    def test_include_related(self):
        response = self.client.get(self.repo1_list_url + "?include_related=my_permissions")
        for c in response.data['data']:
            self.assertIn("my_permissions", c["namespace"]["related_fields"])


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestUiCollectionRemoteViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.remote_data = {
            "name": "rh-certified",
            "url": "https://console.redhat.com/api/automation-hub/",
        }
        self.remote = CollectionRemote.objects.get(name=self.remote_data["name"])
        self.repository = AnsibleRepository.objects.get(name=self.remote_data["name"])

    def test_get_remotes(self):
        # data migration created 2 remotes
        response = self.client.get(get_current_ui_url('remotes-list'))
        self.assertEqual(response.data['meta']['count'], 2)

        for key, value in self.remote_data.items():
            self.assertEqual(response.data['data'][1][key], value)

        repository = response.data['data'][1]['repositories'][0]

        self.assertEqual(repository['name'], self.remote_data["name"])
        self.assertEqual(repository['distributions'][0]['base_path'], self.remote_data["name"])

        # token is not visible in a GET
        self.assertNotIn('token', response.data['data'][1])
