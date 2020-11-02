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
