from django.db import models

from pulp_container.app import models as container_models
from django_lifecycle import LifecycleModelMixin

from galaxy_ng.app.access_control import mixins


class ContainerDistribution(
        container_models.ContainerDistribution,
        LifecycleModelMixin,
        mixins.GroupModelPermissionsMixin):

    class Meta:
        proxy = True
        default_related_name = "%(app_label)s_%(model_name)s"


class ContainerDistroReadme(models.Model):
    container = models.OneToOneField(
        container_models.ContainerDistribution,
        on_delete=models.CASCADE, primary_key=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, null=True)
    text = models.TextField(blank=True)
