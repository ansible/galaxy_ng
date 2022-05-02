"""
Signal handlers for the Galaxy application.
Those signals are loaded by
galaxy_ng.app.__init__:PulpGalaxyPluginAppConfig.ready() method.
"""
from django.apps import apps
from django.dispatch import receiver
from django.db.models.signals import post_save, post_migrate
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository, Collection
from galaxy_ng.app.access_control.statements import PULP_CONTAINER_VIEWSETS
from galaxy_ng.app.models import Namespace
from pulpcore.plugin.models import ContentRedirectContentGuard


@receiver(post_save, sender=AnsibleRepository)
def ensure_retain_repo_versions_on_repository(sender, instance, created, **kwargs):
    """Ensure repository has retain_repo_versions set when created.
    retain_repo_versions defaults to 1 when not set.
    """

    if created and instance.retain_repo_versions is None:
        instance.retain_repo_versions = 1
        instance.save()


@receiver(post_save, sender=AnsibleDistribution)
def ensure_content_guard_exists_on_distribution(sender, instance, created, **kwargs):
    """Ensure distribution have a content guard when created."""

    content_guard = ContentRedirectContentGuard.objects.first()

    if created and instance.content_guard is None:
        instance.content_guard = content_guard
        instance.save()


@receiver(post_save, sender=Collection)
def create_namespace_if_not_present(sender, instance, created, **kwargs):
    """Ensure Namespace object exists when Collection object saved.
    django signal for pulp_ansible Collection model, so that whenever a
    Collection object is created or saved, it will create a Namespace object
    if the Namespace does not already exist.
    Supports use case: In pulp_ansible sync, when a new collection is sync'd
    a new Collection object is created, but the Namespace object is defined
    in galaxy_ng and therefore not created. This signal ensures the
    Namespace is created.
    """

    Namespace.objects.get_or_create(name=instance.namespace)


def set_pulp_container_access_policies(sender, **kwargs):
    apps = kwargs.get("apps")
    if apps is None:
        from django.apps import apps
    AccessPolicy = apps.get_model("core", "AccessPolicy")

    print("Overriding pulp_container access policy")
    for view in PULP_CONTAINER_VIEWSETS:
        policy, created = AccessPolicy.objects.update_or_create(
            viewset_name=view, defaults={**PULP_CONTAINER_VIEWSETS[view], "customized": True})


post_migrate.connect(
    set_pulp_container_access_policies,
    sender=apps.get_app_config("galaxy"),
    dispatch_uid="override_pulp_container_access_policies"
)
