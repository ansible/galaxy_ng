import logging

from django.contrib.auth import models as auth_models
from django.conf import settings
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository

log = logging.getLogger(__name__)

__all__ = (
    'SYSTEM_SCOPE',
    'RH_PARTNER_ENGINEER_GROUP',
    'User',
    'Group',
)


SYSTEM_SCOPE = 'system'
RH_PARTNER_ENGINEER_GROUP = f'{SYSTEM_SCOPE}:partner-engineers'

default_repo_name = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH


class User(auth_models.AbstractUser):
    """Custom user model."""
    pass


class GroupManager(auth_models.GroupManager):
    def create_identity(self, scope, name):
        return super().create(name=self._make_name(scope, name))

    def get_or_create_identity(self, scope, name):
        group, _ = super().get_or_create(name=self._make_name(scope, name))

        # First login for group/org, we need to create a AnsibleDistribution that points to
        # the "golden" Repository
        default_repo = self._create_repo(group, default_repo_name)
        distro = self._create_distribution(group, default_repo)

        log.debug('distro: %s', distro)
        log.debug('group: %s', group)
        log.debug('distro.repository: %s', distro.repository)

        return group, _

    @staticmethod
    def _create_repo(group, repository_name):
        # TODO: the lifetime of the default repo is long, so shouldn't need to look it
        #       up on every auth attempt. ie, cache it.
        # TODO: This may be a reasonable place to hook up a django signal
        try:
            default_repo = AnsibleRepository.objects.get(name=repository_name)
        except AnsibleRepository.DoesNotExist as exc:
            log.exception(exc)
            raise

        return default_repo

    @staticmethod
    def _create_distribution(group, repository):
        distro_name = settings.GALAXY_API_SYNCLIST_NAME_FORMAT.format(
            account_number=group.account_number())

        try:
            distro = AnsibleDistribution.objects.get(name=distro_name, base_path=distro_name)
        except AnsibleDistribution.DoesNotExist as exc:
            log.debug('distro_name: %s exc: %s', distro_name, exc)
            distro, _ = AnsibleDistribution.objects.get_or_create(name=distro_name,
                                                                  base_path=distro_name,
                                                                  repository=repository)
        return distro

    @staticmethod
    def _make_name(scope, name):
        return f'{scope}:{name}'


class Group(auth_models.Group):
    objects = GroupManager()

    class Meta:
        proxy = True

    def account_number(self):
        # maybe import galaxy_ng.app.auth.auth.RH_ACCOUNT_SCOPE if not circular
        scope = 'rh-identity-account'
        if self.name.startswith(scope):
            account = self.name.replace(f"{scope}:", '', 1)
            return account

        # If not a rh-identity-scoped return full group name
        return self.name
