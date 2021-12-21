from pulpcore.plugin.tasking import dispatch
from pulp_ansible.app.models import AnsibleRepository, CollectionVersion
from pulp_ansible.app.tasks.copy import copy_content


def call_copy_task(collection_version, source_repo, dest_repo):
    """Calls pulp_ansible task to copy content from source to destination repo."""
    locks = [source_repo, dest_repo]
    config = [{
        'source_repo_version': source_repo.latest_version().pk,
        'dest_repo': dest_repo.pk,
        'content': [collection_version.pk],
    }]
    return dispatch(
        copy_content,
        args=[config],
        kwargs={},
        exclusive_resources=locks,
    )


def call_remove_task(collection_version, repository):
    """Calls task to remove content from repo."""
    remove_task_args = (collection_version.pk, repository.pk)
    return dispatch(
        _remove_content_from_repository,
        args=remove_task_args,
        kwargs={},
        exclusive_resources=[repository],
    )


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
