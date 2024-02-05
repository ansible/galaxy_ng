from django.db import models
from ansible_base.lib.abstract_models import AbstractOrganization

from .auth import Group


class Organization(AbstractOrganization):
    """An organization model."""
    main_group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='+')

    teams = models.ManyToManyField(Group, through="OrganizationTeam")


class OrganizationTeam(models.Model):
    """A team to organization relationship joint table."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='+')
    team = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='+')

    class Meta:
        constraints = [
            models.UniqueConstraint("organization", "team", name="uq_organization_team"),
        ]
