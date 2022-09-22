import logging
# from django.contrib.auth import default_app_config

from rest_framework import status as http_code

from pulpcore.plugin.util import assign_role
from pulp_ansible.app import models as pulp_ansible_models

from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app import models as galaxy_models
from galaxy_ng.app.models import auth as auth_models

from .base import BaseTestCase, get_current_ui_url

from .synclist_base import ACCOUNT_SCOPE

log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.DEBUG)


class TestUIDistributions(BaseTestCase):
    default_owner_roles = ['galaxy.synclist_owner']

    def setUp(self):
        super().setUp()
        self.user = auth_models.User.objects.create(username='admin')
        self.distro_url = get_current_ui_url('distributions-list')
        self.my_distro_url = get_current_ui_url('my-distributions-list')

        self.group = self._create_group_with_synclist_perms(
            ACCOUNT_SCOPE, "test1_group", users=[self.user]
        )

        self.synclist_repo = self._create_repository('123-synclist')
        self.repo2 = self._create_repository('other-repo')
        self.inbound_repo = self._create_repository('inbound-test')

        self.synclist_distro = self._create_distribution(self.synclist_repo)
        self.repo2_distro = self._create_distribution(self.repo2)
        self.inbound_distro = self._create_distribution(self.inbound_repo)

        upstream_repo = self._create_repository('upstream')
        self.synclist = self._create_synclist(
            '123-synclist',
            self.synclist_repo,
            upstream_repo,
            groups=[self.group]
        )

    def _create_distribution(self, repo):
        return pulp_ansible_models.AnsibleDistribution.objects.create(
            repository=repo, name=repo.name, base_path=repo.name)

    def _create_repository(self, name):
        repo = pulp_ansible_models.AnsibleRepository.objects.create(name=name)
        return repo

    def _create_group_with_synclist_perms(self, scope, name, users=None):
        group, _ = auth_models.Group.objects.get_or_create_identity(scope, name)
        if isinstance(users, auth_models.User):
            users = [users]
        group.user_set.add(*users)
        for role in self.default_owner_roles:
            assign_role(role, group)
        return group

    def _create_synclist(
        self, name, repository, upstream_repository, collections=None, namespaces=None,
        policy=None, groups=None,
    ):
        synclist = galaxy_models.SyncList.objects.create(
            name=name, repository=repository, upstream_repository=upstream_repository)
        if groups:
            groups_to_add = {}
            for group in groups:
                groups_to_add[group] = self.default_owner_roles
            synclist.groups = groups_to_add
        return synclist

    def test_distribution_list(self):
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            self.client.force_authenticate(user=self.user)
            data = self.client.get(self.distro_url).data

            # We expect 6 distros from migrations:
            # - rh-certified
            # - community
            # - validated
            # - published
            # - staging
            # - rejected
            # and one extra distro created for testing
            self.assertEqual(len(data['data']), 7)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            self.client.force_authenticate(user=self.user)
            response = self.client.get(self.distro_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_my_distribution_list(self):
        self.client.force_authenticate(user=self.user)
        data = self.client.get(self.my_distro_url).data
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['pulp_id'], str(self.synclist_distro.pk))
        self.assertEqual(data['data'][0]['repository']['name'], self.synclist_repo.name)
