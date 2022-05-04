from django.db import models
from django_lifecycle import LifecycleModel
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository, Collection
from pulpcore.plugin.models import AutoDeleteObjPermsMixin

from galaxy_ng.app.access_control.mixins import GroupModelPermissionsMixin

from . import namespace as namespace_models


class SyncList(
    LifecycleModel, GroupModelPermissionsMixin, AutoDeleteObjPermsMixin
):

    POLICY_CHOICES = [
        ("exclude", "exclude"),
        ("include", "include"),
    ]

    name = models.CharField(max_length=64, unique=True, blank=False)
    policy = models.CharField(max_length=64, choices=POLICY_CHOICES, default="exclude")

    upstream_repository = models.ForeignKey(
        AnsibleRepository,
        on_delete=models.SET_NULL,
        related_name="upstream_repositories",
        null=True,
        blank=True,
    )
    repository = models.ForeignKey(
        AnsibleRepository,
        on_delete=models.SET_NULL,
        related_name="repositories",
        null=True,
        blank=True,
    )
    distribution = models.ForeignKey(
        AnsibleDistribution, on_delete=models.CASCADE, related_name="distributions"
    )
    collections = models.ManyToManyField(Collection)
    namespaces = models.ManyToManyField(namespace_models.Namespace)
