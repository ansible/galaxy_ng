from __future__ import annotations

from ansible_base.lib.abstract_models import AbstractOrganization, AbstractTeam
from django.conf import settings
from django.db import models
from django_lifecycle import LifecycleModelMixin, hook, BEFORE_CREATE, AFTER_UPDATE

from galaxy_ng.app.models.auth import Group


class OrganizationManager(models.Manager):

    def get_default(self) -> Organization:
        """Return default organization."""
        return self.get(name=settings.DEFAULT_ORGANIZATION_NAME)


class Organization(LifecycleModelMixin, AbstractOrganization):
    """An organization model."""

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="organizations",
        help_text="The list of users in this organization."
    )

    objects = OrganizationManager()

    @hook(AFTER_UPDATE)
    def _after_update(self):
        if self.has_changed("name"):
            for team in self.teams.all():
                group = team.group
                group.name = team.group_name()
                group.save()


class Team(LifecycleModelMixin, AbstractTeam):
    """A team model."""

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="teams",
        help_text="The list of users in this team."
    )
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name='+',
        help_text="Related group record.",
    )

    def group_name(self):
        return f"{self.organization.name}::{self.name}"

    @hook(BEFORE_CREATE)
    def _before_create(self):
        if not hasattr(self, "group"):
            self.group = Group.objects.create(name=self.group_name())

    @hook(AFTER_UPDATE)
    def _after_update(self):
        if self.has_changed("name"):
            self.group.name = self.group_name()
            self.group.save()
