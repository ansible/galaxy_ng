from pulpcore.plugin.tasking import enqueue_with_reservation
from pulp_ansible.app.models import AnsibleRepository, CollectionVersion
from pulp_ansible.app.tasks.copy import copy_content


def call_move_content_task(collection_version, source_repo, dest_repo):
    """Dispatches the move content task
    This is a wrapper to group copy_content and remove_content tasks
    because those 2 must run in sequence ensuring the same locks.
    """
    return enqueue_with_reservation(
        move_content,
        resources=[source_repo, dest_repo],
        kwargs=dict(
            collection_version_pk=collection_version.pk,
            source_repo_pk=source_repo.pk,
            dest_repo_pk=dest_repo.pk,
        ),
    )


def move_content(collection_version_pk, source_repo_pk, dest_repo_pk):
    """Move collection version from one repository to another"""
    source_repo = AnsibleRepository.objects.get(pk=source_repo_pk)

    config = [{
        'source_repo_version': source_repo.latest_version().pk,
        'dest_repo': dest_repo_pk,
        'content': [collection_version_pk],
    }]

    # add content to the destination repo
    copy_content(config)

    # remove content from source repo
    _remove_content_from_repository(collection_version_pk, source_repo_pk)


def _remove_content_from_repository(collection_version_pk, repository_pk):
    """
    Remove a CollectionVersion from a repository.
    Args:
        collection_version_pk: The pk of the CollectionVersion to remove from repository.
        repository_pk: The pk of the AnsibleRepository to remove the CollectionVersion from.
    """
    repository = AnsibleRepository.objects.get(pk=repository_pk)
    qs = CollectionVersion.objects.filter(pk=collection_version_pk)
    with repository.new_version() as new_version:
        new_version.remove_content(qs)
