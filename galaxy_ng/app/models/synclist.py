from django.db import models
from django_lifecycle import LifecycleModel
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository, Collection

from galaxy_ng.app.access_control.mixins import GroupModelPermissionsMixin

from . import namespace as namespace_models


class SyncList(
    LifecycleModel, GroupModelPermissionsMixin
):

    POLICY_CHOICES = [
        ("exclude", "exclude"),
        ("include", "include"),
    ]

    name = models.CharField(max_length=64, unique=True, blank=False)
    policy = models.CharField(max_length=64, choices=POLICY_CHOICES, default="exclude")

    upstream_repository = models.ForeignKey(
        AnsibleRepository,
        null=True,
        on_delete=models.SET_NULL,
        related_name="upstream_repositories",
    )
    repository = models.ForeignKey(
        AnsibleRepository, null=True, on_delete=models.SET_NULL, related_name="repositories"
    )
    distribution = models.ForeignKey(
        AnsibleDistribution,
        null=True,
        on_delete=models.SET_NULL,
        related_name="distributions",
    )
    collections = models.ManyToManyField(Collection)
    namespaces = models.ManyToManyField(namespace_models.Namespace)
