import logging
from pulpcore.plugin.tasking import dispatch
from pulp_ansible.app.tasks.signature import sign

from .promotion import move_collection

log = logging.getLogger(__name__)


def call_sign_and_move_task(signing_service, collection_version, source_repo, dest_repo):
    """Dispatches sign and move task

    This is a wrapper to group sign, copy_content and remove_content tasks
    because those 3 must run in sequence ensuring the same locks.
    """
    log.info(
        'Signing with `%s` and moving collection version `%s` from `%s` to `%s`',
        signing_service.name,
        collection_version.pk,
        source_repo.name,
        dest_repo.name
    )

    return dispatch(
        sign_and_move,
        exclusive_resources=[source_repo, dest_repo],
        kwargs={
            "signing_service_pk": signing_service.pk,
            "collection_version_pk": collection_version.pk,
            "source_repo_pk": source_repo.pk,
            "dest_repo_pk": dest_repo.pk,
        }
    )


def sign_and_move(signing_service_pk, collection_version_pk, source_repo_pk, dest_repo_pk):
    """Sign collection version and then move to the destination repo"""

    # Sign while in the source repository
    sign(
        repository_href=source_repo_pk,
        content_hrefs=[collection_version_pk],
        signing_service_href=signing_service_pk
    )

    # Move content from source to destination
    move_collection(
        cv_pk_list=[collection_version_pk],
        src_repo_pk=source_repo_pk,
        dest_repo_list=[dest_repo_pk],
    )


def call_sign_task(signing_service, repository, content_units):
    """Calls task to sign collection content.
    signing_service: Instance of SigningService
    repository: Instance of AnsibleRepository
    content_units: List of content units UUIDS to sign or '*'
                   to sign all content units under repo
    """
    log.info(
        'Signing on-demand with `%s` on repository `%s` content `%s`',
        signing_service.name,
        repository.name,
        content_units
    )

    return dispatch(
        sign,
        exclusive_resources=[repository],
        kwargs={
            "repository_href": repository.pk,
            "content_hrefs": content_units,
            "signing_service_href": signing_service.pk,
        }
    )
