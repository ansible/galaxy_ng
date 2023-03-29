import hashlib
import json

from django.db import models
from django.db import transaction
from django_lifecycle import LifecycleModel
from django.conf import settings

from pulpcore.plugin.util import get_url

from pulp_ansible.app.models import AnsibleNamespaceMetadata

from galaxy_ng.app.access_control import mixins
from galaxy_ng.app.constants import DeploymentMode

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
    _avatar_url = models.URLField(max_length=256, blank=True)
    description = models.CharField(max_length=256, blank=True)
    resources = models.TextField(blank=True)

    # Used to track the last namespace metadata object that was created
    # from this namespace
    last_created_pulp_metadata = models.ForeignKey(
        AnsibleNamespaceMetadata,
        null=True,
        on_delete=models.SET_NULL,
        related_name="galaxy_namespace"
    )

    @property
    def avatar_url(self):
        # TODO: remove this once we can fix the content app on CRC
        # the content app in crc doesn't work
        if settings.GALAXY_DEPLOYMENT_MODE == DeploymentMode.STANDALONE.value:
            data = self.last_created_pulp_metadata
            if data and data.avatar_sha256:
                return settings.ANSIBLE_API_HOSTNAME + get_url(data) + "avatar/"

        return self._avatar_url

    @avatar_url.setter
    def avatar_url(self, value):
        self._avatar_url = value

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
            "avatar_sha256": None
        }

        if self.last_created_pulp_metadata:
            metadata["avatar_sha256"] = self.last_created_pulp_metadata.avatar_sha256

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
