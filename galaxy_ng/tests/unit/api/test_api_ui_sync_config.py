import logging
from rest_framework import status
from django.urls import reverse
from django.test import override_settings
from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    CollectionRemote
)
from galaxy_ng.app.constants import DeploymentMode
from .base import BaseTestCase

log = logging.getLogger(__name__)


def _create_repo(name, **kwargs):
    repo = AnsibleRepository.objects.create(name=name, **kwargs)
    AnsibleDistribution.objects.create(name=name, base_path=name, repository=repo)
    return repo


def _create_remote(name, url, **kwargs):
    return CollectionRemote.objects.create(
        name=name, url=url, **kwargs
    )


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestUiSyncConfigViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.admin_user = self._create_user("admin")
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.certified_remote = _create_remote(
            name='rh-certified',
            url='https://a.certified.url.com/api/v2/',
            requirements_file=None
        )
        _create_repo(name='rh-certified', remote=self.certified_remote)

        self.community_remote = _create_remote(
            name='community',
            url='https://galaxy.ansible.com',
            requirements_file=(
                "collections:\n"
                "  - name: initial.name\n"
                "    server: initial.content.com\n"
                "    api_key: NotASecret\n"
            )
        )
        _create_repo(name='community', remote=self.community_remote)

    def build_config_url(self, path):
        return reverse('galaxy:api:content:v3:sync-config', kwargs={'path': path})

    def build_sync_url(self, path):
        return reverse('galaxy:api:content:v3:sync', kwargs={'path': path})

    def test_positive_get_config_sync_for_certified(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.build_config_url(self.certified_remote.name))
        log.debug('test_positive_get_config_sync_for_certified')
        log.debug('response: %s', response)
        log.debug('response.data: %s', response.data)
        self.assertEqual(response.data['name'], self.certified_remote.name)
        self.assertEqual(response.data['url'], self.certified_remote.url)
        self.assertEqual(response.data['requirements_file'], None)

    def test_positive_get_config_sync_for_community(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.build_config_url(self.community_remote.name))
        log.debug('test_positive_get_config_sync_for_community')
        log.debug('response: %s', response)
        log.debug('response.data: %s', response.data)
        self.assertEqual(response.data['name'], self.community_remote.name)
        self.assertEqual(response.data['url'], self.community_remote.url)
        self.assertEqual(
            response.data['requirements_file'],
            self.community_remote.requirements_file
        )

    def test_positive_update_certified_repo_data(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.put(
            self.build_config_url(self.certified_remote.name),
            {
                "auth_url": "https://auth.com",
                "token": "TEST",
                "name": "rh-certified",
                "policy": "immediate",
                "requirements_file": None,
                "url": "https://updated.url.com/",
            },
            format='json'
        )
        log.debug('test_positive_update_certified_repo_data')
        log.debug('response: %s', response)
        log.debug('response.data: %s', response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        updated = self.client.get(self.build_config_url(self.certified_remote.name))
        self.assertEqual(updated.data["auth_url"], "https://auth.com")
        self.assertEqual(updated.data["url"], "https://updated.url.com/")
        self.assertIsNone(updated.data["requirements_file"])

    def test_negative_update_community_repo_data_without_requirements_file(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.put(
            self.build_config_url(self.community_remote.name),
            {
                "auth_url": "https://auth.com",
                "name": "community",
                "policy": "immediate",
                "requirements_file": None,
                "url": "https://galaxy.ansible.com/v3/collections",
            },
            format='json'
        )
        log.debug('test_negative_update_community_repo_data_without_requirements_file')
        log.debug('response: %s', response)
        log.debug('response.data: %s', response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            'Syncing content from community domains without specifying a '
            'requirements file is not allowed.',
            str(response.data['errors'])
        )

    def test_positive_update_community_repo_data_with_requirements_file(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.put(
            self.build_config_url(self.community_remote.name),
            {
                "auth_url": "https://auth.com",
                "token": "TEST",
                "name": "community",
                "policy": "immediate",
                "requirements_file": (
                    "collections:\n"
                    "  - name: foo.bar\n"
                    "    server: https://foobar.content.com\n"
                    "    api_key: s3cr3tk3y\n"
                ),
                "url": "https://galaxy.ansible.com/v3/collections/",
            },
            format='json'
        )

        log.debug('test_positive_update_community_repo_data_with_requirements_file')
        log.debug('response: %s', response)
        log.debug('response.data: %s', response.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('foobar.content.com', response.data['requirements_file'])

    def test_positive_syncing_returns_a_task_id(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(self.build_sync_url(self.certified_remote.name))
        log.debug('test_positive_syncing_returns_a_task_id')
        log.debug('response: %s', response)
        log.debug('response.data: %s', response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('task', response.data)

    def test_sensitive_fields_are_not_exposed(self):
        self.client.force_authenticate(user=self.admin_user)
        api_url = self.build_config_url(self.certified_remote.name)
        response = self.client.get(api_url)
        self.assertNotIn('password', response.data)
        self.assertNotIn('token', response.data)
        self.assertNotIn('proxy_password', response.data)

    def test_write_only_fields(self):
        self.client.force_authenticate(user=self.admin_user)
        api_url = self.build_config_url(self.certified_remote.name)
        write_only_fields = ['client_key', 'token', 'password', 'proxy_password']

        # note, proxy url and user have to be set in order to be able to set a
        # proxy password
        request_data = {
            "url": self.certified_remote.url,
            "proxy_url": "https://example.com",
            "proxy_username": "bob"}

        for field in write_only_fields:
            request_data[field] = "value_is_set"

        self.client.put(api_url, request_data, format='json')

        write_only = self.client.get(api_url).data['write_only_fields']
        response_names = set()
        # Check that all write only fields are set
        for field in write_only:
            self.assertEqual(field['is_set'], True)

            # unset all write only fields
            request_data[field['name']] = None
            response_names.add(field['name'])

        self.assertEqual(set(write_only_fields), response_names)
        self.client.put(api_url, request_data, format='json')

        # Check that all write only fields are unset
        write_only = self.client.get(api_url).data['write_only_fields']
        for field in write_only:
            self.assertEqual(field['is_set'], False)
            request_data[field['name']] = ""

        self.client.put(api_url, request_data, format='json')

        write_only = self.client.get(api_url).data['write_only_fields']
        for field in write_only:
            self.assertEqual(field['is_set'], False)

    def test_split_proxy_url_field(self):
        self.client.force_authenticate(user=self.admin_user)

        # ensure proxy_url is blank
        api_url = self.build_config_url(self.certified_remote.name)
        response = self.client.get(api_url)
        self.assertIsNone(response.data['proxy_url'])
        self.assertIsNone(response.data['proxy_username'])

        data = {'name': response.data['name'], 'url': response.data['url']}

        # PUT proxy url without auth
        self.client.put(api_url, {'proxy_url': 'http://proxy.com:4242', **data}, format='json')
        response = self.client.get(api_url)
        self.assertEqual(response.data['proxy_url'], 'http://proxy.com:4242')
        self.assertEqual(response.data['proxy_username'], None)
        self.assertNotIn('proxy_password', response.data)
        instance = CollectionRemote.objects.get(pk=response.data['pk'])
        self.assertEqual(instance.proxy_url, 'http://proxy.com:4242')

        # PUT proxy url with only username
        self.client.put(
            api_url,
            {'proxy_url': 'http://proxy.com:4242', 'proxy_username': 'User1', **data}, format='json'
        )
        response = self.client.get(api_url)
        self.assertEqual(response.data['proxy_url'], 'http://proxy.com:4242')
        self.assertEqual(response.data['proxy_username'], 'User1')
        self.assertNotIn('proxy_password', response.data)
        instance = CollectionRemote.objects.get(pk=response.data['pk'])
        self.assertEqual(instance.proxy_url, 'http://User1@proxy.com:4242')

        # PUT proxy url with username and password
        self.client.put(
            api_url,
            {
                'proxy_url': 'http://proxy.com:4242',
                'proxy_username': 'User1',
                'proxy_password': 'MyPrecious42',
                **data
            },
            format='json'
        )
        response = self.client.get(api_url)
        self.assertEqual(response.data['proxy_url'], 'http://proxy.com:4242')
        self.assertEqual(response.data['proxy_username'], 'User1')
        self.assertNotIn('proxy_password', response.data)
        instance = CollectionRemote.objects.get(pk=response.data['pk'])
        self.assertEqual(instance.proxy_url, 'http://User1:MyPrecious42@proxy.com:4242')

        # Edit password
        self.client.put(api_url, {'proxy_password': 'MyPrecious43', **data}, format='json')
        response = self.client.get(api_url)
        self.assertEqual(response.data['proxy_url'], 'http://proxy.com:4242')
        self.assertEqual(response.data['proxy_username'], 'User1')
        self.assertNotIn('proxy_password', response.data)
        instance = CollectionRemote.objects.get(pk=response.data['pk'])
        self.assertEqual(instance.proxy_url, 'http://User1:MyPrecious43@proxy.com:4242')

        # Edit username
        self.client.put(api_url, {'proxy_username': 'User2', **data}, format='json')
        response = self.client.get(api_url)
        self.assertEqual(response.data['proxy_url'], 'http://proxy.com:4242')
        self.assertEqual(response.data['proxy_username'], 'User2')
        self.assertNotIn('proxy_password', response.data)
        instance = CollectionRemote.objects.get(pk=response.data['pk'])
        self.assertEqual(instance.proxy_url, 'http://User2:MyPrecious43@proxy.com:4242')

        # Edit url using IP
        self.client.put(api_url, {'proxy_url': 'http://192.168.0.42:4242', **data}, format='json')
        response = self.client.get(api_url)
        self.assertEqual(response.data['proxy_url'], 'http://192.168.0.42:4242')
        self.assertEqual(response.data['proxy_username'], 'User2')
        self.assertNotIn('proxy_password', response.data)
        instance = CollectionRemote.objects.get(pk=response.data['pk'])
        self.assertEqual(instance.proxy_url, 'http://User2:MyPrecious43@192.168.0.42:4242')

        # Edit url without scheme
        response = self.client.put(
            api_url, {'proxy_url': '192.168.0.42:4242', **data}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['errors'][0]['detail'], 'Enter a valid URL.')

        # Edit url
        self.client.put(api_url, {'proxy_url': 'http://proxy2.com:4242', **data}, format='json')
        response = self.client.get(api_url)
        self.assertEqual(response.data['proxy_url'], 'http://proxy2.com:4242')
        self.assertEqual(response.data['proxy_username'], 'User2')
        self.assertNotIn('proxy_password', response.data)
        instance = CollectionRemote.objects.get(pk=response.data['pk'])
        self.assertEqual(instance.proxy_url, 'http://User2:MyPrecious43@proxy2.com:4242')

        # Cleanup password
        self.client.put(api_url, {'proxy_password': None, **data}, format='json')
        response = self.client.get(api_url)
        self.assertEqual(response.data['proxy_url'], 'http://proxy2.com:4242')
        self.assertEqual(response.data['proxy_username'], 'User2')
        self.assertNotIn('proxy_password', response.data)
        instance = CollectionRemote.objects.get(pk=response.data['pk'])
        self.assertEqual(instance.proxy_url, 'http://User2@proxy2.com:4242')

        # Cleanup username even if password is set  (avoid http://:1234@...)
        self.client.put(
            api_url, {'proxy_password': '1234', 'proxy_username': None, **data}, format='json'
        )
        response = self.client.get(api_url)
        self.assertEqual(response.data['proxy_url'], 'http://proxy2.com:4242')
        self.assertEqual(response.data['proxy_username'], None)
        self.assertNotIn('proxy_password', response.data)
        instance = CollectionRemote.objects.get(pk=response.data['pk'])
        self.assertEqual(instance.proxy_url, 'http://proxy2.com:4242')

        # Cleanup everything
        self.client.put(api_url, {'proxy_url': None, **data}, format='json')
        response = self.client.get(api_url)
        self.assertEqual(response.data['proxy_url'], None)
        self.assertEqual(response.data['proxy_username'], None)
        self.assertNotIn('proxy_password', response.data)
        instance = CollectionRemote.objects.get(pk=response.data['pk'])
        self.assertEqual(instance.proxy_url, None)
