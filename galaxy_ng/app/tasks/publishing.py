import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from pulpcore.plugin.models import Task
from pulpcore.plugin.tasking import enqueue_with_reservation
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository, CollectionVersion
from pulp_ansible.app.tasks.collections import import_collection

from .promotion import add_content_to_repository, remove_content_from_repository

log = logging.getLogger(__name__)

VERSION_CERTIFIED = "certified"

GOLDEN_NAME = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH
STAGING_NAME = settings.GALAXY_API_STAGING_DISTRIBUTION_BASE_PATH


def get_created_collection_versions():
    current_task = Task.current()
    created_resources = current_task.created_resources.filter(
        content_type_id=ContentType.objects.get_for_model(CollectionVersion))

    # TODO: replace with values_list
    created_collection_versions = []
    for created_resource in created_resources:
        collection_version = created_resource.content_object

        created_collection_versions.append(collection_version)

    return created_collection_versions


def import_and_move_to_staging(temp_file_pk, **kwargs):
    """Import collection version and move to staging repository.

    Custom task to call pulp_ansible's import_collection() task then
    enqueue two tasks to add to staging repo and remove from inbound repo.

    This task will not wait for the enqueued tasks to finish.
    """
    inbound_repository_pk = kwargs.get('repository_pk')
    import_collection(temp_file_pk=temp_file_pk,
                      repository_pk=inbound_repository_pk)

    try:
        staging_repo = AnsibleDistribution.objects.get(name=STAGING_NAME).repository
    except AnsibleRepository.DoesNotExist:
        raise RuntimeError(f'Could not find staging repository: "{STAGING_NAME}"')

    inbound_repo = AnsibleRepository.objects.get(pk=inbound_repository_pk)

    inbound_locks = [inbound_repo]
    staging_locks = [staging_repo]

    created_collection_versions = get_created_collection_versions()

    for collection_version in created_collection_versions:
        # enqueue task to add collection_version to staging repo
        add_task_args = (collection_version.pk, staging_repo.pk)
        enqueue_with_reservation(add_content_to_repository, staging_locks, args=add_task_args)

        # enqueue task to remove collection_verion from inbound repo
        remove_task_args = (collection_version.pk, inbound_repository_pk)
        enqueue_with_reservation(remove_content_from_repository,
                                 inbound_locks, args=remove_task_args)


def import_and_auto_approve(temp_file_pk, **kwargs):
    """Import collection version and automatically approve.

    Custom task to call pulp_ansible's import_collection() task
    then automatically approve collection version so no
    manual approval action needs to occur.
    """
    inbound_repository_pk = kwargs.get('repository_pk')
    import_collection(temp_file_pk=temp_file_pk, repository_pk=inbound_repository_pk)

    try:
        golden_repo = AnsibleDistribution.objects.get(name=GOLDEN_NAME).repository
    except AnsibleRepository.DoesNotExist:
        raise RuntimeError(f'Could not find staging repository: "{GOLDEN_NAME}"')

    inbound_repo = AnsibleRepository.objects.get(pk=inbound_repository_pk)

    remove_locks = [inbound_repo]
    add_locks = [golden_repo]

    created_collection_versions = get_created_collection_versions()

    for collection_version in created_collection_versions:
        collection_version.certification = VERSION_CERTIFIED
        collection_version.save()

        # enqueue task to add collection_version to golden repo
        add_task_args = (collection_version.pk, golden_repo.pk)
        enqueue_with_reservation(add_content_to_repository, add_locks, args=add_task_args)

        # enqueue task to remove collection_verion from inbound repo
        remove_task_args = (collection_version.pk, inbound_repository_pk)
        enqueue_with_reservation(remove_content_from_repository,
                                 remove_locks, args=remove_task_args)

        log.info('Imported and auto approved collection artifact %s to repository %s',
                 collection_version.relative_path,
                 golden_repo.latest_version())
