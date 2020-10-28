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
class TestUiTaskListViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.admin_user = self._create_user("admin")
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.certified_remote = _create_remote(
            name='rh-certified',
            url='https://a.certified.url.com/api/v2/collections',
            requirements_file=None
        )
        _create_repo(name='rh-certified', remote=self.certified_remote)

    def build_sync_url(self, path):
        return reverse('galaxy:api:content:v3:sync', kwargs={'path': path})

    def build_task_url(self):
        return reverse('galaxy:api:v3:default-content:tasks-list')

    def test_tasks_required_fields(self):
        # Spawn a task
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(self.build_sync_url(self.certified_remote.name))
        log.debug('test_positive_syncing_returns_a_task_id')
        log.debug('response: %s', response)
        log.debug('response.data: %s', response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('task', response.data)

        # Ensure all required fields are present
        response = self.client.get(self.build_task_url())
        log.debug('response: %s', response)
        log.debug('response.data: %s', response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['meta']['count'], 0)
        required_fields = (
            'pulp_id',
            'name',
            'created_at',
            'updated_at',
            'finished_at',
            'started_at',
            'state',
            'error',
            'worker',
            'parent_task',
            'child_tasks',
            'repository',
            'progress_reports',
        )
        for field in required_fields:
            self.assertIn(field, response.data['data'][0])
