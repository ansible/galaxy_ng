import urllib
import uuid
from unittest import mock

from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    Collection,
    CollectionVersion,
    CollectionRemote
)
from pulpcore.app.util import get_prn
from pulpcore.plugin.models import Task
from pulpcore.plugin.util import assign_role
from rest_framework import status

from galaxy_ng.app import models
from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.constants import DeploymentMode
from .base import BaseTestCase, get_current_ui_url


def _create_repo(name, **kwargs):
    repo = AnsibleRepository.objects.create(name=name, **kwargs)
    AnsibleDistribution.objects.create(name=name, base_path=name, repository=repo)
    return repo


def _get_create_version_in_repo(namespace, collection, repo, **kwargs):
    collection_version, _ = CollectionVersion.objects.get_or_create(
        namespace=namespace,
        name=collection.name,
        collection=collection,
        sha256=uuid.uuid4().hex,
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
            "url": "https://console.redhat.com/api/automation-hub/content/published/",
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

    def test_get_remote_includes_sync_highest_versions(self):
        response = self.client.get(get_current_ui_url('remotes-list'))
        self.assertIn('sync_highest_versions', response.data['data'][1])
        self.assertIsNone(response.data['data'][1]['sync_highest_versions'])

    def test_get_remote_detail_includes_sync_highest_versions(self):
        detail_url = get_current_ui_url('remotes-detail', kwargs={"pk": str(self.remote.pk)})
        response = self.client.get(detail_url)
        self.assertIn('sync_highest_versions', response.data)
        self.assertIsNone(response.data['sync_highest_versions'])

    def _as_admin(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def test_put_sync_highest_versions(self):
        self._as_admin()
        detail_url = get_current_ui_url('remotes-detail', kwargs={"pk": str(self.remote.pk)})
        put_data = {
            "name": self.remote_data["name"],
            "url": self.remote_data["url"],
            "sync_highest_versions": 1,
        }
        response = self.client.put(detail_url, put_data, format='json')
        self.assertEqual(response.status_code, 200)

        response = self.client.get(detail_url)
        self.assertEqual(response.data['sync_highest_versions'], 1)

    def test_patch_sync_highest_versions(self):
        self._as_admin()
        detail_url = get_current_ui_url('remotes-detail', kwargs={"pk": str(self.remote.pk)})
        patch_data = {
            "url": self.remote_data["url"],
            "sync_highest_versions": 3,
        }
        response = self.client.patch(detail_url, patch_data, format='json')
        self.assertEqual(response.status_code, 200)

        response = self.client.get(detail_url)
        self.assertEqual(response.data['sync_highest_versions'], 3)

    def test_clear_sync_highest_versions(self):
        self._as_admin()
        detail_url = get_current_ui_url('remotes-detail', kwargs={"pk": str(self.remote.pk)})
        self.client.put(detail_url, {
            "name": self.remote_data["name"],
            "url": self.remote_data["url"],
            "sync_highest_versions": 1,
        }, format='json')

        self.client.put(detail_url, {
            "name": self.remote_data["name"],
            "url": self.remote_data["url"],
            "sync_highest_versions": None,
        }, format='json')

        response = self.client.get(detail_url)
        self.assertIsNone(response.data['sync_highest_versions'])

    def test_sync_highest_versions_rejects_zero(self):
        self._as_admin()
        detail_url = get_current_ui_url('remotes-detail', kwargs={"pk": str(self.remote.pk)})
        response = self.client.put(detail_url, {
            "name": self.remote_data["name"],
            "url": self.remote_data["url"],
            "sync_highest_versions": 0,
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_sync_highest_versions_rejects_negative(self):
        self._as_admin()
        detail_url = get_current_ui_url('remotes-detail', kwargs={"pk": str(self.remote.pk)})
        response = self.client.put(detail_url, {
            "name": self.remote_data["name"],
            "url": self.remote_data["url"],
            "sync_highest_versions": -1,
        }, format='json')
        self.assertEqual(response.status_code, 400)


@mock.patch('ansible_base.lib.serializers.mixins.get_setting', return_value=True)
class TestUiCollectionRemoteWrite(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(
            username='remote_admin', is_superuser=True)
        self.client.force_authenticate(user=self.admin_user)
        self.list_url = get_current_ui_url('remotes-list')

    def _detail_url(self, pk):
        return get_current_ui_url('remotes-detail', kwargs={'pk': str(pk)})

    def _task_from_href(self, task_href):
        task_pk = str(task_href).rstrip('/').split('/')[-1]
        return Task.objects.get(pk=task_pk)

    def test_create_and_delete_remote(self, mock_get_setting):
        response = self.client.post(self.list_url, {
            "name": "test_collection_remote_1",
            "url": "https://example.com/api/",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['name'], 'test_collection_remote_1')
        pk = response.data['pk']

        detail_url = self._detail_url(pk)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test_collection_remote_1')

        # destroy dispatches pulpcore's async remote delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task', response.data)

    def test_delete_task_reserves_remote_and_linked_repositories(self, mock_get_setting):
        remote = CollectionRemote.objects.create(
            name='reserve_remote', url='https://example.com/api/')
        linked = AnsibleRepository.objects.create(
            name='reserve_linked_repo',
            remote=remote,
            last_synced_metadata_time=timezone.now(),
        )
        # Never-synced repos are not reserved by pulp's CollectionRemoteViewSet.
        AnsibleRepository.objects.create(
            name='reserve_unsynced_repo', remote=remote)

        response = self.client.delete(self._detail_url(remote.pk))
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        task = self._task_from_href(response.data['task'])

        reserved = task.reserved_resources_record or []
        self.assertIn(get_prn(remote), reserved)
        self.assertIn(get_prn(linked), reserved)
        unsynced = AnsibleRepository.objects.get(name='reserve_unsynced_repo')
        self.assertNotIn(get_prn(unsynced), reserved)

    def test_unprivileged_user_cannot_delete_remote(self, mock_get_setting):
        remote = CollectionRemote.objects.create(
            name='nope_delete_remote', url='https://example.com/api/')
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self._detail_url(remote.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(CollectionRemote.objects.filter(pk=remote.pk).exists())

    def test_delete_and_sync_cannot_run_concurrently(self, mock_get_setting):
        remote = CollectionRemote.objects.create(
            name='overlap_remote', url='https://example.com/api/')
        repo = AnsibleRepository.objects.create(
            name='overlap_repo',
            remote=remote,
            last_synced_metadata_time=timezone.now(),
        )
        AnsibleDistribution.objects.create(
            name='overlap_distro', base_path='overlap_distro', repository=repo)

        sync_response = self.client.post(
            reverse('galaxy:api:v3:sync', kwargs={'path': 'overlap_distro'}))
        self.assertEqual(sync_response.status_code, status.HTTP_200_OK, sync_response.data)
        sync_task = Task.objects.get(pk=sync_response.data['task'])

        delete_response = self.client.delete(self._detail_url(remote.pk))
        self.assertEqual(
            delete_response.status_code, status.HTTP_202_ACCEPTED, delete_response.data)
        delete_task = self._task_from_href(delete_response.data['task'])

        remote_prn = get_prn(remote)
        self.assertIn(remote_prn, sync_task.reserved_resources_record or [])
        self.assertIn(remote_prn, delete_task.reserved_resources_record or [])

    def test_dangerous_name_rejected_on_create(self, mock_get_setting):
        response = self.client.post(self.list_url, {
            "name": "<script>alert(1)</script>",
            "url": "https://example.com/api/",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertFalse(
            CollectionRemote.objects.filter(name="<script>alert(1)</script>").exists())

    def test_duplicate_name_rejected_on_create(self, mock_get_setting):
        payload = {
            "name": "duplicate_collection_remote",
            "url": "https://example.com/api/",
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(
            CollectionRemote.objects.filter(name='duplicate_collection_remote').count(), 1)

    def test_create_keep_password_hint_never_inherits_existing_proxy_password(
        self, mock_get_setting,
    ):
        existing = self._create_proxy_remote(
            'create_keep_hint_existing', 'existing-secret',
        )
        existing_url = existing.url

        response = self.client.post(
            self.list_url,
            {
                'name': existing.name,
                'url': 'https://attacker.example.com/api/',
                'proxy_url': 'http://proxy.example.com:4242',
                'proxy_username': 'attacker-user',
                'proxy_password': None,
                'write_only_fields': [{'name': 'proxy_password', 'is_set': True}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        existing.refresh_from_db()
        self.assertEqual(existing.proxy_password, 'existing-secret')
        self.assertEqual(existing.url, existing_url)
        self.assertEqual(
            CollectionRemote.objects.filter(name=existing.name).count(),
            1,
        )

        response = self.client.post(
            self.list_url,
            {
                'name': 'create_keep_hint_new_remote',
                'url': 'https://create_keep_hint_new.example.com/api/',
                'proxy_password': None,
                'write_only_fields': [{'name': 'proxy_password', 'is_set': True}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        new_remote = CollectionRemote.objects.get(name='create_keep_hint_new_remote')
        self.assertNotEqual(new_remote.proxy_password, existing.proxy_password)
        self.assertFalse(new_remote.proxy_password)

    def test_unprivileged_user_cannot_create_remote(self, mock_get_setting):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, {
            "name": "nope_remote",
            "url": "https://example.com/api/",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(CollectionRemote.objects.filter(name='nope_remote').exists())

    def test_creator_with_only_add_perm_can_update_and_delete(self, mock_get_setting):
        # add_collectionremote is enough to POST; the pulp creation hook must
        # then grant galaxy.collection_remote_owner so PATCH/DELETE succeed.
        creator = auth_models.User.objects.create(username='remote_creator')
        creator.user_permissions.add(Permission.objects.get(
            content_type__app_label='ansible',
            codename='add_collectionremote',
        ))
        self.client.force_authenticate(user=creator)

        response = self.client.post(self.list_url, {
            "name": "owned_by_creator_remote",
            "url": "https://example.com/api/",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        detail_url = self._detail_url(response.data['pk'])

        response = self.client.patch(
            detail_url, {"url": "https://example.com/updated/"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        self.assertIn('task', response.data)

    def test_name_cannot_be_renamed_on_update(self, mock_get_setting):
        remote = CollectionRemote.objects.create(
            name='rename_guard_remote', url='https://example.com/api/')
        response = self.client.patch(self._detail_url(remote.pk), {
            "name": "renamed_should_not_stick",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        remote.refresh_from_db()
        self.assertEqual(remote.name, 'rename_guard_remote')

    def _create_proxy_remote(self, name, password):
        return CollectionRemote.objects.create(
            name=name,
            url=f'https://{name}.example.com/api/',
            proxy_url='http://proxy.example.com:4242',
            proxy_username=f'{name}-user',
            proxy_password=password,
        )

    def test_patch_omitting_proxy_password_preserves_it(self, mock_get_setting):
        remote = self._create_proxy_remote('keep_proxy_pw_remote', 'keep-me')
        response = self.client.patch(self._detail_url(remote.pk), {
            "url": "https://example.com/updated/",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        remote.refresh_from_db()
        self.assertEqual(remote.proxy_password, 'keep-me')

    def test_write_only_hint_does_not_copy_another_remote_proxy_password(self, mock_get_setting):
        remote_a = self._create_proxy_remote('proxy_pw_remote_a', 'password-a')
        remote_b = self._create_proxy_remote('proxy_pw_remote_b', 'password-b')

        response = self.client.patch(self._detail_url(remote_a.pk), {
            "name": remote_b.name,
            "proxy_password": None,
            "write_only_fields": [{"name": "proxy_password", "is_set": True}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        remote_a.refresh_from_db()
        remote_b.refresh_from_db()
        self.assertEqual(remote_a.proxy_password, 'password-a')
        self.assertEqual(remote_b.proxy_password, 'password-b')

    def test_owner_patch_with_forged_name_does_not_copy_other_proxy_password(
        self, mock_get_setting,
    ):
        owner_a = auth_models.User.objects.create(username='remote_owner_a')
        owner_b = auth_models.User.objects.create(username='remote_owner_b')

        remote_a = self._create_proxy_remote('owner_proxy_remote_a', 'password-a')
        remote_b = self._create_proxy_remote('owner_proxy_remote_b', 'password-b')
        assign_role('galaxy.collection_remote_owner', owner_a, obj=remote_a)
        assign_role('galaxy.collection_remote_owner', owner_b, obj=remote_b)

        self.client.force_authenticate(user=owner_a)
        response = self.client.patch(self._detail_url(remote_a.pk), {
            "name": remote_b.name,
            "proxy_password": None,
            "write_only_fields": [{"name": "proxy_password", "is_set": True}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        remote_a.refresh_from_db()
        remote_b.refresh_from_db()
        self.assertEqual(remote_a.proxy_password, 'password-a')
        self.assertEqual(remote_b.proxy_password, 'password-b')

        response = self.client.patch(self._detail_url(remote_b.pk), {
            "url": "https://evil.example.com/api/",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        remote_b.refresh_from_db()
        self.assertEqual(
            remote_b.url,
            'https://owner_proxy_remote_b.example.com/api/',
        )

    def test_patch_keep_hint_preserves_proxy_password(self, mock_get_setting):
        remote = self._create_proxy_remote('patch_keep_hint_remote', 'patch-keep-me')
        response = self.client.patch(self._detail_url(remote.pk), {
            "url": "https://example.com/updated/",
            "proxy_password": None,
            "write_only_fields": [{"name": "proxy_password", "is_set": True}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        remote.refresh_from_db()
        self.assertEqual(remote.proxy_password, 'patch-keep-me')

    def test_patch_new_password_with_keep_hint_replaces_proxy_password(
        self, mock_get_setting,
    ):
        remote = self._create_proxy_remote('patch_replace_hint_remote', 'old-secret')
        response = self.client.patch(self._detail_url(remote.pk), {
            "proxy_url": remote.proxy_url,
            "proxy_username": remote.proxy_username,
            "proxy_password": "brand-new-secret",
            "write_only_fields": [{"name": "proxy_password", "is_set": True}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        remote.refresh_from_db()
        self.assertEqual(remote.proxy_password, 'brand-new-secret')

    def test_patch_explicit_null_clears_proxy_password(self, mock_get_setting):
        remote = self._create_proxy_remote('patch_clear_pw_remote', 'clear-me')
        response = self.client.patch(self._detail_url(remote.pk), {
            "proxy_username": None,
            "proxy_password": None,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        remote.refresh_from_db()
        self.assertFalse(remote.proxy_password)
        self.assertIsNone(remote.proxy_username)

    def test_patch_empty_proxy_password_returns_400_not_500(self, mock_get_setting):
        remote = self._create_proxy_remote('patch_empty_pw_remote', 'keep-me')
        response = self.client.patch(self._detail_url(remote.pk), {
            "proxy_password": "",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        remote.refresh_from_db()
        self.assertEqual(remote.proxy_password, 'keep-me')

    def test_patch_write_only_fields_hints_do_not_500(self, mock_get_setting):
        remote = self._create_proxy_remote('hint_no_500_remote', 'hint-secret')
        valid_cases = {
            'absent': {},
            'empty_list': {'write_only_fields': []},
            'non_proxy_hint': {'write_only_fields': [{'name': 'token', 'is_set': True}]},
        }
        for label, hint_extra in valid_cases.items():
            with self.subTest(hint=label):
                payload = {
                    'url': f'https://{label}.hint-no-500.example.com/api/',
                    **hint_extra,
                }
                response = self.client.patch(
                    self._detail_url(remote.pk), payload, format='json',
                )
                self.assertNotEqual(
                    response.status_code,
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    response.data,
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        invalid_cases = {
            'non_dict_entry': {'write_only_fields': ['token']},
            'dict_without_name': {'write_only_fields': [{'is_set': True}]},
            'non_list': {'write_only_fields': {'name': 'proxy_password', 'is_set': True}},
        }
        for label, hint_extra in invalid_cases.items():
            with self.subTest(hint=label):
                payload = {
                    'url': f'https://{label}.hint-invalid.example.com/api/',
                    **hint_extra,
                }
                response = self.client.patch(
                    self._detail_url(remote.pk), payload, format='json',
                )
                self.assertNotEqual(
                    response.status_code,
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    response.data,
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                    response.data,
                )

        remote.refresh_from_db()
        self.assertEqual(remote.proxy_password, 'hint-secret')

    def test_put_keep_hint_preserves_proxy_password(self, mock_get_setting):
        remote = self._create_proxy_remote('put_keep_hint_remote', 'put-keep-me')
        response = self.client.put(self._detail_url(remote.pk), {
            "name": remote.name,
            "url": remote.url,
            "proxy_url": remote.proxy_url,
            "proxy_username": remote.proxy_username,
            "proxy_password": None,
            "write_only_fields": [{"name": "proxy_password", "is_set": True}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        remote.refresh_from_db()
        self.assertEqual(remote.proxy_password, 'put-keep-me')

    def test_put_new_password_with_keep_hint_replaces_proxy_password(
        self, mock_get_setting,
    ):
        remote = self._create_proxy_remote('put_replace_hint_remote', 'old-secret')
        response = self.client.put(self._detail_url(remote.pk), {
            "name": remote.name,
            "url": remote.url,
            "proxy_url": remote.proxy_url,
            "proxy_username": remote.proxy_username,
            "proxy_password": "brand-new-secret",
            "write_only_fields": [{"name": "proxy_password", "is_set": True}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        remote.refresh_from_db()
        self.assertEqual(remote.proxy_password, 'brand-new-secret')

    def test_put_forged_name_keep_hint_does_not_copy_other_proxy_password(
        self, mock_get_setting,
    ):
        remote_a = self._create_proxy_remote('put_forged_remote_a', 'password-a')
        remote_b = self._create_proxy_remote('put_forged_remote_b', 'password-b')
        response = self.client.put(self._detail_url(remote_a.pk), {
            "name": remote_b.name,
            "url": remote_a.url,
            "proxy_url": remote_a.proxy_url,
            "proxy_username": remote_a.proxy_username,
            "proxy_password": None,
            "write_only_fields": [{"name": "proxy_password", "is_set": True}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        remote_a.refresh_from_db()
        remote_b.refresh_from_db()
        self.assertEqual(remote_a.proxy_password, 'password-a')
        self.assertEqual(remote_b.proxy_password, 'password-b')
