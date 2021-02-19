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
