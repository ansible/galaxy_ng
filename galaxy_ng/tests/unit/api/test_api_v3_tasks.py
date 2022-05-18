import logging
from rest_framework import status
from django.urls import reverse
from django.test import override_settings
from pulp_ansible.app.models import CollectionRemote
from galaxy_ng.app.constants import DeploymentMode
from .base import BaseTestCase

log = logging.getLogger(__name__)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestUiTaskListViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.admin_user = self._create_user("admin")
        self.sync_group = self._create_group(
            "", "admins", self.admin_user, ["galaxy.collection_admin"])
        self.admin_user.save()

        self.certified_remote = CollectionRemote.objects.get(name='rh-certified')

    def build_sync_url(self, path):
        return reverse('galaxy:api:v3:sync', kwargs={'path': path})

    def build_task_url(self):
        return reverse('galaxy:api:v3:tasks-list')

    def build_task_detail_url(self, pk):
        return reverse('galaxy:api:v3:tasks-detail', kwargs={"pk": pk})

    def test_tasks_required_fields(self):
        # Spawn a task
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(self.build_sync_url(self.certified_remote.name))
        log.debug('Spawn a task for testing tasks/ endpoint')
        log.debug('response: %s', response)
        log.debug('response.data: %s', response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('task', response.data)

        # Ensure all required fields are present in list URL
        response = self.client.get(self.build_task_url())
        log.debug('response: %s', response)
        log.debug('response.data: %s', response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['meta']['count'], 0)
        required_fields = (
            'pulp_id',
            'name',
            'finished_at',
            'started_at',
            'state',
            'href',
        )
        for field in required_fields:
            self.assertIn(field, response.data['data'][0])

        # Test Detail URL
        task_pk = response.data['data'][0]['pulp_id']
        response = self.client.get(self.build_task_detail_url(task_pk))
        log.debug('response: %s', response)
        log.debug('response.data: %s', response.data)
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
            'progress_reports',
        )
        for field in required_fields:
            self.assertIn(field, response.data)
