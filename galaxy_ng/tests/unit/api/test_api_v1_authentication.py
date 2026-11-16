from rest_framework.test import APIRequestFactory, force_authenticate

from galaxy_ng.app.access_control.statements.legacy import LEGACY_STATEMENTS
from galaxy_ng.app.api.v1.models import LegacyRoleImport
from galaxy_ng.app.api.v1.views import LegacyRootView
from galaxy_ng.app.api.v1.viewsets.roles import LegacyRoleImportsViewSet, LegacyRolesViewSet
from galaxy_ng.app.utils.galaxy import uuid_to_int
from galaxy_ng.tests.unit.api.base import BaseTestCase

from pulpcore.plugin.models import Task


class TestLegacyApiAuthentication(BaseTestCase):
    def test_legacy_root_allows_anonymous(self):
        request = APIRequestFactory().get("/")

        response = LegacyRootView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("roles", response.data)

    def test_legacy_root_allows_authenticated_users(self):
        request = APIRequestFactory().get("/")
        force_authenticate(request, user=self.user)

        response = LegacyRootView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("roles", response.data)

    def test_legacy_read_allows_anonymous(self):
        read_statements = LEGACY_STATEMENTS["LegacyAccessPolicy"][0]
        request = APIRequestFactory().get('/api/v1/roles/')
        response = LegacyRolesViewSet.as_view({'get': 'list'})(request)

        self.assertEqual(read_statements["principal"], "*")
        self.assertEqual(response.status_code, 200)

    def test_legacy_write_requires_authentication(self):
        request = APIRequestFactory().delete('/api/v1/roles/1/')
        response = LegacyRolesViewSet.as_view({'delete': 'destroy'})(request, pk='1')

        self.assertEqual(response.status_code, 401)

    def test_legacy_task_messages_hidden_from_anonymous(self):
        task = Task.objects.create(name='test-import', state='COMPLETED')
        LegacyRoleImport.objects.create(
            task=task,
            messages=[{
                'state': 'COMPLETED',
                'level': 'INFO',
                'time': 0,
                'message': 'alternate_clone_url: https://user:secret@github.com/x/y',
            }],
        )
        task_id = uuid_to_int(str(task.pulp_id))

        view = LegacyRoleImportsViewSet.as_view({'get': 'list'})
        request = APIRequestFactory().get(f'/api/v1/imports/?id={task_id}')
        response = view(request)

        self.assertEqual(response.status_code, 200)
        messages = response.data['results'][0]['summary_fields']['task_messages']
        self.assertEqual(messages, [])

        request = APIRequestFactory().get(f'/api/v1/imports/?id={task_id}')
        force_authenticate(request, user=self.user)
        response = view(request)

        self.assertEqual(response.status_code, 200)
        messages = response.data['results'][0]['summary_fields']['task_messages']
        self.assertEqual(len(messages), 1)

    def test_legacy_task_detail_messages_hidden_from_anonymous(self):
        task = Task.objects.create(name='test-import', state='COMPLETED')
        LegacyRoleImport.objects.create(
            task=task,
            messages=[{
                'state': 'COMPLETED',
                'level': 'INFO',
                'time': 0,
                'message': 'alternate_clone_url: https://user:secret@github.com/x/y',
            }],
        )

        view = LegacyRoleImportsViewSet.as_view({'get': 'list'})
        request = APIRequestFactory().get('/api/v1/imports/?detail=1')
        response = view(request)

        self.assertEqual(response.status_code, 200)
        for result in response.data['results']:
            self.assertEqual(result['summary_fields']['task_messages'], [])

        request = APIRequestFactory().get('/api/v1/imports/?detail=1')
        force_authenticate(request, user=self.user)
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            any(result['summary_fields']['task_messages'] for result in response.data['results'])
        )
