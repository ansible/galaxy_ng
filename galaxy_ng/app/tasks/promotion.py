from pulpcore.plugin.tasking import dispatch
from pulp_ansible.app.models import (
    AnsibleRepository,
    CollectionVersion,
    CollectionVersionSignature
)
from pulp_ansible.app.tasks.copy import copy_content


def move_content(collection_version_pk, source_repo_pk, dest_repo_pk):
    """Move collection version from one repository to another"""
    # Copy to the destination repo including the content signatures
    source_repo = AnsibleRepository.objects.get(pk=source_repo_pk)
    signatures = CollectionVersionSignature.objects.filter(
        signed_collection=collection_version_pk,
        pk__in=source_repo.content.values_list("pk", flat=True)
    ).values_list("pk", flat=True)
    content = [collection_version_pk]
    if signatures:
        content += signatures

    config = [{
        'source_repo_version': source_repo.latest_version().pk,
        'dest_repo': dest_repo_pk,
        'content': content,
    }]

    copy_content(config)

    # remove old content from source repo
    _remove_content_from_repository(collection_version_pk, source_repo_pk, signatures)


def call_move_content_task(collection_version, source_repo, dest_repo):
    """Dispatches the move content task

    This is a wrapper to group copy_content and remove_content tasks
    because those 2 must run in sequence ensuring the same locks.

    """
    return dispatch(
        move_content,
        exclusive_resources=[source_repo, dest_repo],
        kwargs=dict(
            collection_version_pk=collection_version.pk,
            source_repo_pk=source_repo.pk,
            dest_repo_pk=dest_repo.pk
        )
    )


def _remove_content_from_repository(collection_version_pk, repository_pk, signatures_pk=None):
    """
    Remove a CollectionVersion from a repository.
    Args:
        collection_version_pk: The pk of the CollectionVersion to remove from repository.
        repository_pk: The pk of the AnsibleRepository to remove the CollectionVersion from.
        signatures_pk: A list of pks of the CollectionVersionSignatures to remove from the repo.
    """
    repository = AnsibleRepository.objects.get(pk=repository_pk)
    qs = CollectionVersion.objects.filter(pk=collection_version_pk)
    with repository.new_version() as new_version:
        new_version.remove_content(qs)
        if signatures_pk:
            sigs = CollectionVersionSignature.objects.filter(pk__in=signatures_pk)
            new_version.remove_content(sigs)
