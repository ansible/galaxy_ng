import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository, CollectionVersion
from pulp_ansible.app.tasks.collections import import_collection
from pulpcore.plugin.models import Task
from pulpcore.plugin.models import SigningService

from .promotion import call_move_content_task
from .signing import call_sign_and_move_task

log = logging.getLogger(__name__)

GOLDEN_NAME = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH
STAGING_NAME = settings.GALAXY_API_STAGING_DISTRIBUTION_BASE_PATH
AUTO_SIGN = settings.get("GALAXY_AUTO_SIGN_COLLECTIONS", False)
SIGNING_SERVICE_NAME = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE", "ansible-default")


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
        raise RuntimeError(_('Could not find staging repository: "%s"') % STAGING_NAME)

    inbound_repo = AnsibleRepository.objects.get(pk=inbound_repository_pk)

    created_collection_versions = get_created_collection_versions()

    for collection_version in created_collection_versions:
        call_move_content_task(collection_version, inbound_repo, staging_repo)

        if settings.GALAXY_ENABLE_API_ACCESS_LOG:
            _log_collection_upload(
                kwargs["username"],
                kwargs["expected_namespace"],
                kwargs["expected_name"],
                kwargs["expected_version"]
            )


def import_and_auto_approve(temp_file_pk, **kwargs):
    """Import collection version and automatically approve.

    Custom task to call pulp_ansible's import_collection() task
    then automatically approve collection version so no
    manual approval action needs to occur.
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
        golden_repo = AnsibleDistribution.objects.get(name=GOLDEN_NAME).repository
    except AnsibleRepository.DoesNotExist:
        raise RuntimeError(_('Could not find staging repository: "%s"') % GOLDEN_NAME)

    inbound_repo = AnsibleRepository.objects.get(pk=inbound_repository_pk)

    created_collection_versions = get_created_collection_versions()

    try:
        signing_service = AUTO_SIGN and SigningService.objects.get(name=SIGNING_SERVICE_NAME)
    except SigningService.DoesNotExist:
        raise RuntimeError(_('Signing %s service not found') % SIGNING_SERVICE_NAME)

    for collection_version in created_collection_versions:
        move_task_params = {
            "collection_version": collection_version,
            "source_repo": inbound_repo,
            "dest_repo": golden_repo,
        }
        if AUTO_SIGN:
            call_sign_and_move_task(signing_service, **move_task_params)
        else:
            call_move_content_task(**move_task_params)

        log.info(
            'Imported and auto approved collection artifact %s to repository %s',
            collection_version.relative_path,
            golden_repo.latest_version()
        )

        if settings.GALAXY_ENABLE_API_ACCESS_LOG:
            _log_collection_upload(
                kwargs["username"],
                kwargs["expected_namespace"],
                kwargs["expected_name"],
                kwargs["expected_version"]
            )


def _log_collection_upload(username, namespace, name, version):
    api_access_log = logging.getLogger("automated_logging")
    api_access_log.info(
        "Collection uploaded by user '%s': %s-%s-%s",
        username,
        namespace,
        name,
        version,
    )
