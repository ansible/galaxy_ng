from django.contrib.auth import models as auth_models


__all__ = (
    'SYSTEM_SCOPE',
    'RH_PARTNER_ENGINEER_GROUP',
    'User',
    'Group',
)


SYSTEM_SCOPE = 'system'
RH_PARTNER_ENGINEER_GROUP = f'{SYSTEM_SCOPE}:partner-engineers'


class User(auth_models.AbstractUser):
    """Custom user model."""
    pass


class GroupManager(auth_models.GroupManager):
    def create_identity(self, scope, name):
        return super().create(name=self._make_name(scope, name))

    def get_or_create_identity(self, scope, name):
        return super().get_or_create(name=self._make_name(scope, name))

    @staticmethod
    def _make_name(scope, name):
        return f'{scope}:{name}'


class Group(auth_models.Group):
    objects = GroupManager()

    class Meta:
        proxy = True
