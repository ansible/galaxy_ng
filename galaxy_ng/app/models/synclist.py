from django.db import models

from pulpcore.plugin.models import AutoDeleteObjPermsMixin
from pulp_ansible.app.models import AnsibleRepository, Collection
from django_lifecycle import LifecycleModel

from galaxy_ng.app.access_control.mixins import GroupModelPermissionsMixin

from . import namespace as namespace_models


class SyncList(LifecycleModel, GroupModelPermissionsMixin, AutoDeleteObjPermsMixin):
    POLICY_CHOICES = [
        ("blacklist", "blacklist"),
        ("whitelist", "whitelist"),
    ]

    OWNER_PERMISSIONS = [
        'galaxy.view_synclist',
        'galaxy.update_synclist',
    ]

    name = models.CharField(max_length=64, unique=True, blank=False)
    policy = models.CharField(max_length=64, choices=POLICY_CHOICES, default="blacklist")

    repository = models.ForeignKey(AnsibleRepository, on_delete=models.CASCADE)
    collections = models.ManyToManyField(Collection)
    namespaces = models.ManyToManyField(namespace_models.Namespace)
