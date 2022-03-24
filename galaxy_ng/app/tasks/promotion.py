from pulpcore.plugin.tasking import add_and_remove, dispatch
from pulp_ansible.app.models import CollectionVersionSignature


def call_move_content_task(collection_version, source_repo, dest_repo):
    """Dispatches the move content task

    This is a wrapper to group copy_content and remove_content tasks
    because those 2 must run in sequence ensuring the same locks.

    """

    signatures_pks = CollectionVersionSignature.objects.filter(
        signed_collection=collection_version.pk,
        pk__in=source_repo.content.values_list("pk", flat=True)
    ).values_list("pk", flat=True)

    return dispatch(
        move_content,
        exclusive_resources=[source_repo, dest_repo],
        kwargs=dict(
            collection_version_pk=collection_version.pk,
            source_repo_pk=source_repo.pk,
            dest_repo_pk=dest_repo.pk,
            signatures_pks=list(signatures_pks),
        ),
    )


def move_content(collection_version_pk, source_repo_pk, dest_repo_pk, signatures_pks=None):
    """Move collection version + signatures from one repository to another"""

    content = [collection_version_pk]
    if signatures_pks:
        content += signatures_pks

    # add content to the destination repo
    add_and_remove(
        dest_repo_pk,
        add_content_units=content,
        remove_content_units=[],
    )

    # remove content from source repo
    add_and_remove(
        source_repo_pk,
        add_content_units=[],
        remove_content_units=content,
    )
