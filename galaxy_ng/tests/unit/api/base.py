from unittest import mock

from django.conf import settings
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.models import auth as auth_models
from pulpcore.plugin.util import assign_role
from galaxy_ng.app import constants


API_PREFIX = settings.GALAXY_API_PATH_PREFIX.strip("/")

MOCKED_RH_IDENTITY = {
    'entitlements': {
        'insights': {
            'is_entitled': True
        },
        'smart_management': {
            'is_entitled': True
        },
        'openshift': {
            'is_entitled': True
        },
        'hybrid': {
            'is_entitled': True
        }
    },
    'identity': {
        'account_number': '6269497',
        'type': 'User',
        'user': {
            'username': 'ansible-insights',
            'email': 'fabricio.campineiro@bancoamazonia.com.br',
            'first_name': 'Ansible',
            'last_name': 'Insights',
            'is_active': True,
            'is_org_admin': True,
            'is_internal': False,
            'locale': 'en_US'
        },
        'internal': {
            'org_id': '52814875'
        }
    }
}


def get_current_ui_url(namespace, **kwargs):
    return reverse('galaxy:api:ui:{version}:{namespace}'.format(
        version=constants.CURRENT_UI_API_VERSION,
        namespace=namespace
    ), **kwargs)


class BaseTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = self._create_user('test')
        self.client.force_authenticate(user=self.user)

        # Mock RH identity header
        patcher = mock.patch.object(
            access_policy.AccessPolicyBase, "_get_rh_identity", return_value=MOCKED_RH_IDENTITY
        )

        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _create_user(username):
        return auth_models.User.objects.create(username=username)

    @staticmethod
    def _create_group(scope, name, users=None, roles=[]):
        group, _ = auth_models.Group.objects.get_or_create_identity(scope, name)
        if isinstance(users, auth_models.User):
            users = [users]
        group.user_set.add(*users)
        for r in roles:
            assign_role(r, group)
        return group

    @staticmethod
    def _create_namespace(name, groups=None):
        groups = groups or []
        namespace = models.Namespace.objects.create(name=name)
        if isinstance(groups, auth_models.Group):
            groups = [groups]

        groups_to_add = {}
        for group in groups:
            groups_to_add[group] = [
                'galaxy.collection_namespace_owner',
            ]
        namespace.groups = groups_to_add
        return namespace

    @staticmethod
    def _create_partner_engineer_group():
        # Maintain PE Group consistency with
        # galaxy_ng/app/management/commands/maintain-pe-group.py:28
        pe_roles = [
            'galaxy.collection_namespace_owner',
            'galaxy.collection_admin',
            'galaxy.user_admin',
            'galaxy.group_admin',
            'galaxy.content_admin',
        ]
        pe_group = auth_models.Group.objects.create(
            name='partner-engineers')

        for role in pe_roles:
            assign_role(role, pe_group)

        return pe_group
