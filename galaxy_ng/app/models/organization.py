from ansible_base.lib.abstract_models import AbstractOrganization
from django.conf import settings
from django.db import models


class OrganizationManager(models.Manager):

    def get_default(self):
        return self.get(name=settings.DEFAULT_ORGANIZATION_NAME)


class Organization(AbstractOrganization):
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="organizations",
        help_text="The list of users in this organization.",
    )

    objects = OrganizationManager()
