import logging

from rest_framework import status

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.constants import DeploymentMode

from .base import BaseTestCase, get_current_ui_url

log = logging.getLogger(__name__)


class TestUiNamespaceViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(username='admin')
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.user_url = get_current_ui_url('users-list')
        self.me_url = get_current_ui_url('me')

    def test_user_list(self):
        self.client.force_authenticate(user=self.user)
        log.debug('self.client: %s', self.client)
        log.debug('self.client.__dict__: %s', self.client.__dict__)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.user_url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.user_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data['data']
            self.assertEqual(len(data), auth_models.User.objects.all().count())

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.user_url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_get(self):
        url = '{}{}/'.format(self.user_url, self.user.id)

        # Users can view themselves
        self.client.force_authenticate(user=self.user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # But not other users
        url = '{}{}/'.format(self.user_url, self.admin_user.id)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        url = '{}{}/'.format(self.user_url, self.user.id)
        self.client.force_authenticate(user=self.admin_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data
            self.assertEqual(data['email'], self.user.email)
            self.assertEqual(data['first_name'], self.user.first_name)
            self.assertEqual(len(data['groups']), self.user.groups.all().count())
            for group in data['groups']:
                self.assertTrue(self.user.groups.exists(id=group['id']))

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def _test_create_or_update(self, method_call, url, new_user_data, crud_status, auth_user):
        self.client.force_authenticate(user=auth_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = method_call(self.user_url, new_user_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            # set user with invalid password
            new_user_data['password'] = '12345678'
            response = method_call(url, new_user_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            error_messages = set([])
            for err in response.data['errors']:
                error_messages.add(err['code'])

            desired_errors = set(
                ['password_too_short', 'password_too_common', 'password_entirely_numeric'])

            self.assertEqual(error_messages, desired_errors)

            # set valid user
            new_user_data['password'] = 'trekkie4Lyfe1701'
            response = method_call(url, new_user_data, format='json')
            self.assertEqual(response.status_code, crud_status)
            data = response.data
            self.assertEqual(data['email'], new_user_data['email'])
            self.assertEqual(data['first_name'], new_user_data['first_name'])
            self.assertEqual(data['groups'], new_user_data['groups'])
            self.assertFalse(
                self.client.login(username=new_user_data['username'], password='bad'))
            self.assertTrue(
                self.client.login(
                    username=new_user_data['username'], password=new_user_data['password']))

    def test_user_create(self):
        new_user_data = {
            'username': 'test2',
            'first_name': 'First',
            'last_name': 'Last',
            'email': 'email@email.com',
            'groups': [{
                'id': self.pe_group.id,
                'name': self.pe_group.name
            }]
        }

        self.client.force_authenticate(user=self.user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.post(self.user_url, new_user_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self._test_create_or_update(
            self.client.post,
            self.user_url,
            new_user_data,
            status.HTTP_201_CREATED,
            self.admin_user)

    def test_user_update(self):
        user = auth_models.User.objects.create(username='test2')
        put_url = '{}{}/'.format(self.user_url, user.id)
        user.groups.add(self.pe_group)
        user.save()
        new_user_data = {
            'username': 'test2',
            'first_name': 'First',
            'last_name': 'Last',
            'email': 'email@email.com',
            'groups': [{
                'id': self.pe_group.id,
                'name': self.pe_group.name
            }]
        }

        self.client.force_authenticate(user=self.user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.put(put_url, new_user_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self._test_create_or_update(
            self.client.put, put_url, new_user_data, status.HTTP_200_OK, self.admin_user)

    def test_me_get(self):
        self.client.force_authenticate(user=self.user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.me_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertFalse(response.data['is_partner_engineer'])
            self.assertEqual(response.data['username'], self.user.username)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.me_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertFalse(response.data['is_partner_engineer'])
            self.assertEqual(response.data['username'], self.user.username)

    def test_me_update(self):
        user = auth_models.User.objects.create(username='me_test')
        user.save()
        new_user_data = {
            'username': 'test2',
            'first_name': 'First',
            'last_name': 'Last',
            'email': 'email@email.com',
            'groups': []
        }

        self._test_create_or_update(
            self.client.put, self.me_url, new_user_data, status.HTTP_200_OK, user)
