import logging

from django.conf import settings
from pulpcore.plugin.models import ContentArtifact
from pulpcore.plugin.tasking import enqueue_with_reservation
from pulp_ansible.app.models import AnsibleRepository
from pulp_ansible.app.tasks.collections import import_collection

from .promotion import add_content_to_repository, remove_content_from_repository

log = logging.getLogger(__name__)

VERSION_CERTIFIED = "certified"

GOLDEN_NAME = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH
STAGING_NAME = settings.GALAXY_API_STAGING_DISTRIBUTION_BASE_PATH


def import_and_move_to_staging(artifact_pk, **kwargs):
    """Import collection version and move to staging repository.

    Custom task to call pulp_ansible's import_collection() task then
    enqueue two tasks to add to staging repo and remove from inbound repo.

    This task will not wait for the enqueued tasks to finish.
    """
    inbound_repository_pk = kwargs.get('repository_pk')
    import_collection(artifact_pk=artifact_pk, repository_pk=inbound_repository_pk)

    content_artifact = ContentArtifact.objects.get(artifact_id=artifact_pk)
    collection_version = content_artifact.content.ansible_collectionversion

    # enqueue task to add collection_version to staging repo
    try:
        staging_repo = AnsibleRepository.objects.get(name=STAGING_NAME)
    except AnsibleRepository.DoesNotExist:
        raise RuntimeError(f'Could not find staging repository: "{STAGING_NAME}"')
    locks = [staging_repo]
    task_args = (collection_version.pk, staging_repo.pk)
    enqueue_with_reservation(add_content_to_repository, locks, args=task_args)

    # enqueue task to remove collection_verion from inbound repo
    inbound_repo = AnsibleRepository.objects.get(pk=inbound_repository_pk)
    locks = [inbound_repo]
    task_args = (collection_version.pk, inbound_repository_pk)
    enqueue_with_reservation(remove_content_from_repository, locks, args=task_args)


def import_and_auto_approve(artifact_pk, **kwargs):
    """Import collection version and automatically approve.

    Custom task to call pulp_ansible's import_collection() task
    then automatically approve collection version so no
    manual approval action needs to occur.
    """
    inbound_repository_pk = kwargs.get('repository_pk')
    import_collection(artifact_pk=artifact_pk, repository_pk=inbound_repository_pk)
    content_artifact = ContentArtifact.objects.get(artifact_id=artifact_pk)
    collection_version = content_artifact.content.ansible_collectionversion

    # FIXME: remove when no longer using certification flag
    collection_version.certification = VERSION_CERTIFIED
    collection_version.save()

    # enqueue task to add collection_version to golden repo
    try:
        golden_repo = AnsibleRepository.objects.get(name=GOLDEN_NAME)
    except AnsibleRepository.DoesNotExist:
        raise RuntimeError(f'Could not find golden repository: "{GOLDEN_NAME}"')
    locks = [golden_repo]
    task_args = (collection_version.pk, golden_repo.pk)
    enqueue_with_reservation(add_content_to_repository, locks, args=task_args)

    # enqueue task to remove collection_verion from inbound repo
    inbound_repo = AnsibleRepository.objects.get(pk=inbound_repository_pk)
    locks = [inbound_repo]
    task_args = (collection_version.pk, inbound_repository_pk)
    enqueue_with_reservation(remove_content_from_repository, locks, args=task_args)
