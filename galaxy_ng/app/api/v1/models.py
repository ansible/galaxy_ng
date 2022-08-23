from django.conf import settings
from django.db import models

from galaxy_ng.app.models import Namespace


class LegacyNamespace(models.Model):

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
