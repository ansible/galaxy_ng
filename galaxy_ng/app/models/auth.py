import logging

from django.contrib.auth import models as auth_models

from pulpcore.plugin.models import Group as PulpGroup

log = logging.getLogger(__name__)

__all__ = (
    "SYSTEM_SCOPE",
    "RH_PARTNER_ENGINEER_GROUP",
    "User",
    "Group",
)


SYSTEM_SCOPE = "system"
RH_PARTNER_ENGINEER_GROUP = f"{SYSTEM_SCOPE}:partner-engineers"


class User(auth_models.AbstractUser):
    """Custom user model."""

    pass


class GroupManager(auth_models.GroupManager):
    def create_identity(self, scope, name):
        return super().create(name=self._make_name(scope, name))

    def get_or_create_identity(self, scope, name):
        group, _ = super().get_or_create(name=self._make_name(scope, name))

        return group, _

    @staticmethod
    def _make_name(scope, name):
        return f"{scope}:{name}"


class Group(PulpGroup):
    objects = GroupManager()

    class Meta:
        proxy = True

    def account_number(self):
        scope = "rh-identity-account"
        if self.name.startswith(scope):
            account = self.name.replace(f"{scope}:", "", 1)
            return account

        # If not a rh-identity-scoped return full group name
        return self.name
