from __future__ import annotations

from ansible_base.lib.abstract_models import AbstractOrganization, AbstractTeam
from django.conf import settings
from django.db import models


class OrganizationManager(models.Manager):

    def get_default(self) -> Organization:
        """Return default organization."""
        return self.get(name=settings.DEFAULT_ORGANIZATION_NAME)


class Organization(AbstractOrganization):
    """An organization model."""

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="organizations",
        help_text="The list of users in this organization."
    )

    objects = OrganizationManager()


class Team(AbstractTeam):
    """A team model."""

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="teams",
        help_text="The list of users in this team."
    )
