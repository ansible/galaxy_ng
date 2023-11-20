from django.db import models

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models.auth import User

from pulpcore.plugin.models import Task


class LegacyNamespace(models.Model):
    """
    A legacy namespace, aka a github username.

    Namespaces in the galaxy_ng sense are very restrictive
    with their character sets. This is primarily due to how
    collection namespaces and names must be pythonic and
    importable module names. Legacy roles had no such
    restrictions and were 1:1 with whatever github allowed
    for a username.

    This model exists for a few reasons:
        1) enable an endpoint for v1/users with no sql hacks
        2) enable the ui to list namespaces with avatar icons
        3) to map the legacy namespace to a new namespace
           which can have galaxy_ng style permission management
        4) to define what users aside from the creator can
           "own" the roles under the namespace.
    """

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=64, unique=True, blank=False)
    company = models.CharField(max_length=64, blank=True)
    email = models.CharField(max_length=256, blank=True)
    avatar_url = models.URLField(max_length=256, blank=True)
    description = models.CharField(max_length=256, blank=True)

    namespace = models.ForeignKey(
        Namespace,
        null=True,
        on_delete=models.SET_NULL,
        related_name="namespace",
    )

    owners = models.ManyToManyField(
        User,
        editable=True
    )

    def __repr__(self):
        return f'<LegacyNamespace: {self.name}>'

    def __str__(self):
        return self.name
