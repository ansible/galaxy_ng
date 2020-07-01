from unittest import mock

from django.conf import settings
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.models import auth as auth_models
from guardian.shortcuts import assign_perm
from galaxy_ng.app import constants


API_PREFIX = settings.GALAXY_API_PATH_PREFIX.strip("/")


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

        # Permission mock
        patcher = mock.patch.object(
            access_policy.AccessPolicyBase, "has_rh_entitlements", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _create_user(username):
        return auth_models.User.objects.create(username=username)

    @staticmethod
    def _create_group(scope, name, users=None):
        group, _ = auth_models.Group.objects.get_or_create_identity(scope, name)
        if isinstance(users, auth_models.User):
            users = [users]
        group.user_set.add(*users)
        return group

    @staticmethod
    def _create_namespace(name, groups=None):
        namespace = models.Namespace.objects.create(name=name)
        if isinstance(groups, auth_models.Group):
            groups = [groups]

        groups_to_add = {}
        for group in groups:
            groups_to_add[group] = ['galaxy.upload_to_namespace', 'galaxy.change_namespace']
        namespace.groups = groups_to_add
        return namespace

    @staticmethod
    def _create_partner_engineer_group():
        pe_perms = [
            # namespaces
            'galaxy.add_namespace',
            'galaxy.change_namespace',
            'galaxy.upload_to_namespace',

            # collections
            'ansible.modify_ansible_repo_content',

            # users
            'galaxy.view_user',
            'galaxy.delete_user',
            'galaxy.add_user',
            'galaxy.change_user',

            # synclists
            'galaxy.delete_synclist',
            'galaxy.change_synclist',
            'galaxy.view_synclist',
            'galaxy.add_synclist',

            # sync config
            'ansible.change_collectionremote',
        ]
        pe_group = auth_models.Group.objects.create(
            name='partner-engineers')

        for perm in pe_perms:
            assign_perm(perm, pe_group)

        return pe_group
