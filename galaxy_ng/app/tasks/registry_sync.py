
from pulp_container.app.tasks.synchronize import synchronize as container_sync
from pulpcore.plugin.tasking import dispatch

from galaxy_ng.app import models


def launch_container_remote_sync(remote, registry, repository):
    for key, value in registry.get_connection_fields().items():
        setattr(remote, key, value)
        remote.save()

    return dispatch(
        container_sync,
        shared_resources=[remote],
        exclusive_resources=[repository],
        kwargs={
            "remote_pk": str(remote.pk),
            "repository_pk": str(repository.pk),
            "mirror": True,
            "signed_only": False,
        },
    )


def sync_all_repos_in_registry(registry_pk):
    registry = models.ContainerRegistryRemote.objects.get(pk=registry_pk)
    for remote_rel in models.ContainerRegistryRepos.objects.filter(registry=registry).all():
        remote = remote_rel.repository_remote

        for repo in remote.repository_set.all():
            repo.cast()
            launch_container_remote_sync(remote, registry, repo)
