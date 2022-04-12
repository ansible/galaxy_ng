from django.conf import settings
from django.db import models
from django.contrib.postgres import fields as psql_fields


class LegacyNamespace(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=64, unique=True, blank=False)
    company = models.CharField(max_length=64, blank=True)
    email = models.CharField(max_length=256, blank=True)
    avatar_url = models.URLField(max_length=256, blank=True)
    description = models.CharField(max_length=256, blank=True)
    resources = models.TextField(blank=True)

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

    full_metadata = psql_fields.JSONField(
        null=False,
        default=dict
    )

    metadata = psql_fields.JSONField(
        null=False,
        default=dict
    )
