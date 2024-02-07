from ansible_base.lib.abstract_models import AbstractOrganization, AbstractTeam
from django.db import models
from django_lifecycle import BEFORE_CREATE, BEFORE_UPDATE, LifecycleModelMixin, hook

from .auth import Group

GROUP_ORG_PREFIX = "org::"
GROUP_TEAM_PREFIX = "team:{0}::"


class Organization(LifecycleModelMixin, AbstractOrganization):
    """An organization model."""

    group = models.OneToOneField(Group, on_delete=models.CASCADE)

    def _group_name(self):
        return f"{GROUP_ORG_PREFIX}{self.name}"

    @hook(BEFORE_CREATE)
    def _before_create(self):
        if not hasattr(self, "group"):
            self.group = Group.objects.create(name=self._group_name())

    @hook(BEFORE_UPDATE)
    def _before_update(self):
        if self.has_changed("name"):
            self.group.name = self._group_name()


class Team(LifecycleModelMixin, AbstractTeam):
    """A team model."""

    group = models.OneToOneField(Group, on_delete=models.CASCADE)

    def _group_name(self):
        prefix = GROUP_TEAM_PREFIX.format(self.organization.id)
        return f"{prefix}{self.name}"

    @hook(BEFORE_CREATE)
    def _before_create(self):
        if not hasattr(self, "group"):
            self.group = Group.objects.create(name=self._group_name())

    @hook(BEFORE_UPDATE)
    def _before_update(self):
        if self.has_changed("name"):
            self.group.name = self._group_name()
