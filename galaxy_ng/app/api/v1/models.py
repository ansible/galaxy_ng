from django.conf import settings
from django.db import models

from galaxy_ng.app.models import Namespace


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
        settings.AUTH_USER_MODEL,
        related_name='legacy_namespaces',
        editable=True
    )


class LegacyRole(models.Model):
    """
    A legacy v1 role, which is just an index for github.

    These are not "content" in the pulp sense. They are simply
    an index of repositories on github.com that have the shape
    of a standalone role. Nothing is stored on disk or served
    out to the client from the server besides json metadata.

    Sometimes they have versions and sometimes not, hence
    there is no LegacyRoleVersion model.

    Rather than make many many fields and many many models
    to encapsulate the various type of data for a role, this model
    uses a json field to store everything. It is effectively
    mimic'ig a NOSQL database in that regard. Instead of
    adding new fields here as requirements change, store the new
    data in the full_metadata field and alter the serializer
    to expose that new data or to munge old data. For example,
    the docs_blob is a key inside full_metadata.
    """

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    namespace = models.ForeignKey(
        'LegacyNamespace',
        related_name='roles',
        editable=False,
        on_delete=models.PROTECT
    )

    name = models.CharField(max_length=64, unique=False, blank=False)

    full_metadata = models.JSONField(
        null=False,
        default=dict
    )
