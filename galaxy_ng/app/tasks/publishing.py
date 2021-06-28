import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from pulpcore.plugin.models import Task
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository, CollectionVersion
from pulp_ansible.app.tasks.collections import import_collection

from .promotion import call_copy_task, call_remove_task

log = logging.getLogger(__name__)

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
    import_collection(
        temp_file_pk=temp_file_pk,
        repository_pk=inbound_repository_pk,
        expected_namespace=kwargs['expected_namespace'],
        expected_name=kwargs['expected_name'],
        expected_version=kwargs['expected_version'],
    )

    try:
        staging_repo = AnsibleDistribution.objects.get(name=STAGING_NAME).repository
    except AnsibleRepository.DoesNotExist:
        raise RuntimeError(f'Could not find staging repository: "{STAGING_NAME}"')

    inbound_repo = AnsibleRepository.objects.get(pk=inbound_repository_pk)

    created_collection_versions = get_created_collection_versions()

    for collection_version in created_collection_versions:
        call_copy_task(collection_version, inbound_repo, staging_repo)
        call_remove_task(collection_version, inbound_repo)


def get_dest_repo_for_inbound_repo(inbound_repo):
    """Given an inbound AnsibleRepository, lookup/find it's destination repo

    This could be the 'golden' repo, or another repo.

    For the simple case, 'inbound-myrepo' should return the 'myrepo' repo.

    Returns:
        AnsibleRepository
    """

    log.debug('inbound_repo: %s', inbound_repo)

    dest_repo_name = GOLDEN_NAME

    # the "old" way
    try:
        dest_repo = AnsibleDistribution.objects.get(name=dest_repo_name).repository
    except AnsibleRepository.DoesNotExist:
        raise RuntimeError(f'Could not find destination repository: "{dest_repo_name}"')

    return dest_repo


def import_and_auto_approve(temp_file_pk, **kwargs):
    """Import collection version and automatically approve.

    Custom task to call pulp_ansible's import_collection() task
    then automatically approve collection version so no
    manual approval action needs to occur.
    """
    log.debug('kwargs=%s', repr(kwargs))
    inbound_repository_pk = kwargs.get('repository_pk')
    import_collection(
        temp_file_pk=temp_file_pk,
        repository_pk=inbound_repository_pk,
        expected_namespace=kwargs['expected_namespace'],
        expected_name=kwargs['expected_name'],
        expected_version=kwargs['expected_version'],
    )

    inbound_repo = AnsibleRepository.objects.get(pk=inbound_repository_pk)

    # TODO(558): Instead of always trying to promote to the 'golden' repo, we
    #            want to promote to the repo corresponding to the inbound repo
    #            ie, 'inbound-myrepo' -> 'myrepo'
    dest_repo = get_dest_repo_for_inbound_repo(inbound_repo)

    log.debug('dest_repo=%s', dest_repo)

    created_collection_versions = get_created_collection_versions()

    for collection_version in created_collection_versions:
        # TODO(558) dest_repo will be the repo associated with inbound
        call_copy_task(collection_version, inbound_repo, dest_repo)
        call_remove_task(collection_version, inbound_repo)

        log.info('Imported and auto approved collection artifact %s to repository %s',
                 collection_version.relative_path,
                 dest_repo.latest_version())
