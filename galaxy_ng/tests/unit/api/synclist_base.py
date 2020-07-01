import logging
import os.path

from django.test import override_settings
from django.urls import reverse

from rest_framework import status as http_code

from pulp_ansible.app import models as pulp_ansible_models

from galaxy_ng.app.api import permissions
from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app import models as galaxy_models
from galaxy_ng.app.models import auth as auth_models

from .base import BaseTestCase

log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.DEBUG)


@override_settings(FIXTURE_DIRS=[os.path.join(os.path.dirname(__file__), "fixtures")])
class BaseSyncListViewSet(BaseTestCase):
    fixtures = ['synclists.json']
    url_name = 'galaxy:api:v3:ui:synclists-list'

    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(username='admin')
        self.pe_group = auth_models.Group.objects.create(
            name=permissions.IsPartnerEngineer.GROUP_NAME)
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.synclists_url = reverse(self.url_name)
        # self.me_url = reverse('galaxy:api:v3:ui:me')
        self.group1 = auth_models.Group.objects.create(name='test1_group')
        self.user1 = auth_models.User.objects.create_user(username="test1", password="test1-secret")
        self.user1.groups.add(self.group1)
        self.user1.save()
        self.group1.user_set.add(self.user1)
        self.group1.save()

        self.user.groups.add(self.group1)
        self.user.save()

        self.default_repo = pulp_ansible_models.AnsibleRepository.objects.get(name="automation-hub")
        log.debug('self.user: %s groups: %s', self.user, self.user.groups)
        log.debug('self.user1: %s groups: %s', self.user1, self.user1.groups)
        log.debug('self.group1: %s', self.group1)

    def _create_repository(self, name):
        repo = pulp_ansible_models.AnsibleRepository.objects.create(name='test_repo1')
        return repo

    def _create_synclist(self, name, repository, collections=None, namespaces=None,
                         policy=None, users=None, groups=None, upstream_repository=None):
        upstream_repository = upstream_repository or self.default_repo
        groups = groups or [self.group1]
        synclist = galaxy_models.SyncList.objects.create(name=name,
                                                         repository=repository,
                                                         upstream_repository=upstream_repository)
        synclist.groups.set(groups)
        return synclist

    def test_list_no_auth(self):
        self.client.force_authenticate(user=None)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            log.debug('response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)
