from pulpcore.plugin import PulpPluginAppConfig
from django.db.models.signals import post_migrate
from galaxy_ng.app.access_control.statements import PULP_CONTAINER_VIEWSETS


class PulpGalaxyPluginAppConfig(PulpPluginAppConfig):
    """Entry point for the galaxy plugin."""

    name = "galaxy_ng.app"
    label = "galaxy"
    version = "4.3.4"

    def ready(self):
        super().ready()
        post_migrate.connect(
            set_pulp_container_access_policies,
            sender=self,
            dispatch_uid="override_pulp_container_access_policies"
        )


def set_pulp_container_access_policies(sender, **kwargs):
    apps = kwargs.get("apps")
    if apps is None:
        from django.apps import apps
    AccessPolicy = apps.get_model("core", "AccessPolicy")

    print("Overriding pulp_container access poliicy")
    for view in PULP_CONTAINER_VIEWSETS:
        policy, created = AccessPolicy.objects.update_or_create(
            viewset_name=view, defaults={**PULP_CONTAINER_VIEWSETS[view], "customized": True})
