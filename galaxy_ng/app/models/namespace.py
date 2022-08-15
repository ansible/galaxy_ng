import contextlib
from django.db import models
from django.db import transaction
from django.db import IntegrityError
from django_lifecycle import LifecycleModel
from pulp_ansible.app.models import AnsibleRepository, AnsibleDistribution

from galaxy_ng.app.access_control import mixins
from galaxy_ng.app.constants import INBOUND_REPO_NAME_FORMAT

__all__ = ("Namespace", "NamespaceLink")


def create_inbound_repo(name):
    """Creates inbound repo and inbound distribution for namespace publication."""
    inbound_name = INBOUND_REPO_NAME_FORMAT.format(namespace_name=name)
    with contextlib.suppress(IntegrityError):
        # IntegrityError is suppressed for when the named repo/distro already exists
        # In that cases the error handling is performed on the caller.
        repo = AnsibleRepository.objects.create(name=inbound_name, retain_repo_versions=1)
        AnsibleDistribution.objects.create(
            name=inbound_name,
            base_path=inbound_name,
            repository=repo
        )


def delete_inbound_repo(name):
    """Deletes inbound repo and distro in case of namespace deletion."""
    inbound_name = INBOUND_REPO_NAME_FORMAT.format(namespace_name=name)
    with contextlib.suppress(AnsibleRepository.DoesNotExist):
        AnsibleRepository.objects.get(name=inbound_name).delete()
    with contextlib.suppress(AnsibleDistribution.DoesNotExist):
        AnsibleDistribution.objects.get(name=inbound_name).delete()


class NamespaceManager(models.Manager):

    def create(self, **kwargs):
        """Override to create inbound repo and distro."""
        create_inbound_repo(kwargs['name'])
        return super().create(**kwargs)

    def bulk_create(self, objs, **kwargs):
        for obj in objs:
            create_inbound_repo(obj.name)
        return super().bulk_create(objs, **kwargs)

    def get_or_create(self, *args, **kwargs):
        ns, created = super().get_or_create(*args, **kwargs)
        if created:
            create_inbound_repo(kwargs['name'])
        return ns, created


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
    # Cutom manager to handle inbound repo and distro

    objects = NamespaceManager()

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

    def delete(self, *args, **kwargs):
        delete_inbound_repo(self.name)
        return super().delete(*args, **kwargs)

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
