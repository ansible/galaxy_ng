import logging
from unittest import mock

from django.conf import settings
from guardian import shortcuts

from pulp_ansible.app import models as pulp_ansible_models

from galaxy_ng.app import models as galaxy_models
from galaxy_ng.app.access_control.statements import INSIGHTS_STATEMENTS
from galaxy_ng.app.models import auth as auth_models

from . import base

log = logging.getLogger(__name__)

ACCOUNT_SCOPE = "rh-identity-account"

SYNCLIST_PERMS = [
    "add_synclist",
    "view_synclist",
    "delete_synclist",
    "change_synclist",
]


log.info("settings.FIXTURE_DIRS(module scope): %s", settings.FIXTURE_DIRS)


class BaseSyncListViewSet(base.BaseTestCase):
    url_name = "galaxy:api:v3:ui:synclists-list"
    default_owner_permissions = SYNCLIST_PERMS

    def setUp(self):
        super().setUp()

        self.repo = self._create_repository("test_post_repo")
        self.repo.save()

        repo_name = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH
        self.default_repo, _ = pulp_ansible_models.AnsibleRepository.objects.get_or_create(
            name=repo_name
        )

        self.default_dist, _ = pulp_ansible_models.AnsibleDistribution.objects.get_or_create(
            name=repo_name, base_path=repo_name, repository=self.default_repo
        )

        patcher = mock.patch(
            "galaxy_ng.app.access_control." "access_policy.AccessPolicyBase._get_statements",
            return_value=INSIGHTS_STATEMENTS,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _create_group_with_synclist_perms(scope, name, users=None):
        group, _ = auth_models.Group.objects.get_or_create_identity(scope, name)
        if isinstance(users, auth_models.User):
            users = [users]
        group.user_set.add(*users)

        for perm in SYNCLIST_PERMS:
            shortcuts.assign_perm(f"galaxy.{perm}", group)
        return group

    def _create_repository(self, name):
        repo, _ = pulp_ansible_models.AnsibleRepository.objects.get_or_create(name="test_repo1")
        return repo

    def _create_synclist(
        self,
        name,
        repository,
        collections=None,
        namespaces=None,
        policy=None,
        users=None,
        groups=None,
        upstream_repository=None,
    ):
        upstream_repository = upstream_repository or self.default_repo
        if isinstance(groups, auth_models.Group):
            groups = [groups]
        else:
            groups = groups or []

        groups_to_add = {}
        for group in groups:
            groups_to_add[group] = self.default_owner_permissions

        synclist, _ = galaxy_models.SyncList.objects.get_or_create(
            name=name, repository=repository, upstream_repository=upstream_repository,
        )

        synclist.groups = groups_to_add
        synclist.save()

        return synclist
