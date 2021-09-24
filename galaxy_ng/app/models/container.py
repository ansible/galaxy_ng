from django.db import models
from pulpcore.plugin import models as pulp_models
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


class ContainerNamespace(
        container_models.ContainerNamespace,
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


class ContainerRegistryRemote(
    pulp_models.Remote,
    mixins.GroupModelPermissionsMixin,
):

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"

    RED_HAT_REGISTY_DOMAINS = (
        'registry.redhat.io',
    )

    def get_connection_fields(self):
        copy_fields = (
            "url",
            "policy",
            "username",
            "password",
            "tls_validation",
            "client_key",
            "client_cert",
            "ca_cert",
            "download_concurrency",
            "proxy_url",
            "proxy_username",
            "proxy_password",
            "rate_limit",
        )

        result = {}

        for field in copy_fields:
            result[field] = getattr(self, field)

        return result

    def get_registry_backend(self):
        for registry in self.RED_HAT_REGISTY_DOMAINS:
            if registry in self.url:
                return 'redhat'
        return None


class ContainerRegistryRepos(models.Model):
    registry = models.ForeignKey(
        ContainerRegistryRemote,
        on_delete=models.CASCADE,
    )
    repository_remote = models.OneToOneField(
        container_models.ContainerRemote,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="registry"
    )
