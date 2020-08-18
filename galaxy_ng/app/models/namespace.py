from django.db import models
from django.db import transaction
from django_lifecycle import LifecycleModel
from pulpcore.plugin.models import AutoDeleteObjPermsMixin

from galaxy_ng.app.access_control import mixins


__all__ = ("Namespace", "NamespaceLink")


class Namespace(LifecycleModel, mixins.GroupModelPermissionsMixin, AutoDeleteObjPermsMixin):
    """
    A model representing Ansible content namespace.

    Fields:
        name: Namespace name. Must be lower case containing only alphanumeric
            characters and underscores.
        company: Optional namespace owner company name.
        email: Optional namespace contact email.
        avatar_url: Optional namespace logo URL.
        description: Namespace brief description.
        resources: Namespace resources page in markdown format.

    Relations:
        owners: Reference to namespace owners.
        links: Back reference to related links.

    """

    # Fields

    name = models.CharField(max_length=64, unique=True, blank=False)
    company = models.CharField(max_length=64, blank=True)
    email = models.CharField(max_length=256, blank=True)
    avatar_url = models.URLField(max_length=256, blank=True)
    description = models.CharField(max_length=256, blank=True)
    resources = models.TextField(blank=True)

    def __str__(self):
        return self.name

    @transaction.atomic
    def set_links(self, links):
        """Replace namespace related links with new ones."""
        self.links.all().delete()
        self.links.bulk_create(
            NamespaceLink(name=link["name"], url=link["url"], namespace=self)
            for link in links
        )

    class Meta:
        permissions = (
            ('upload_to_namespace', 'Can upload collections to namespace'),
        )


class NamespaceLink(LifecycleModel):
    """
    A model representing a Namespace link.

    Fields:
        name: Link name (e.g. Homepage, Documentation, etc.).
        url: Link URL.

    Relations:
        namespace: Reference to a parent namespace.
    """

    # Fields
    name = models.CharField(max_length=32)
    url = models.URLField(max_length=256)

    # References
    namespace = models.ForeignKey(
        Namespace, on_delete=models.CASCADE, related_name="links"
    )

    def __str__(self):
        return self.name
