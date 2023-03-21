import hashlib
import json

from django.db import models
from django.db import transaction
from django_lifecycle import LifecycleModel

from galaxy_ng.app.access_control import mixins

__all__ = ("Namespace", "NamespaceLink")


class Namespace(LifecycleModel, mixins.GroupModelPermissionsMixin):
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

    @property
    def metadata_sha256(self):
        """Calculates the metadata_sha256 from the other metadata fields."""
        metadata = {
            "name": self.name,
            "company": self.company,
            "email": self.email,
            "description": self.description,
            "resources": self.resources,
            "links": {x.name: x.url for x in self.links.all()},
            "avatar_url": self.avatar_url,
        }
        metadata_json = json.dumps(metadata, sort_keys=True).encode("utf-8")
        hasher = hashlib.sha256(metadata_json)
        return hasher.hexdigest()

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
