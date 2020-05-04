from django.db import models

from pulp_ansible.app.models import AnsibleRepository, Collection

from . import auth as auth_models
from . import namespace as namespace_models


class SyncList(models.Model):
    POLICY_CHOICES = [
        ("blacklist", "blacklist"),
        ("whitelist", "whitelist"),
    ]

    groups = models.ManyToManyField(auth_models.Group, related_name="synclists")
    users = models.ManyToManyField(auth_models.User, related_name="synclists")

    name = models.CharField(max_length=64, unique=True, blank=False)
    policy = models.CharField(max_length=64, choices=POLICY_CHOICES, default="blacklist")

    repository = models.ForeignKey(AnsibleRepository, on_delete=models.CASCADE)
    collections = models.ManyToManyField(Collection)
    namespaces = models.ManyToManyField(namespace_models.Namespace)
