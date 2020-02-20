from django.contrib.auth import models as auth_models


__all__ = (
    'SYSTEM_SCOPE',
    'User',
    'Group',
)


SYSTEM_SCOPE = 'system'


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
