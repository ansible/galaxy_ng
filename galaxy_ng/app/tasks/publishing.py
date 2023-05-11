import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from pulp_ansible.app.models import AnsibleRepository, CollectionVersion

from pulpcore.plugin.tasking import general_create, add_and_remove, dispatch
from pulpcore.plugin.models import Task

from galaxy_ng.app.models import Namespace

from .promotion import call_auto_approve_task

log = logging.getLogger(__name__)

GOLDEN_NAME = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH
STAGING_NAME = settings.GALAXY_API_STAGING_DISTRIBUTION_BASE_PATH
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


def _upload_collection(**kwargs):
    # don't add the collection to the repository in general_create, so that
    # we don't have to lock the repo while the import is running
    repo_pk = kwargs.pop("repository_pk")
    general_args = kwargs.pop("general_args")
    try:
        repo = AnsibleRepository.objects.get(pk=repo_pk)
    except AnsibleRepository.DoesNotExist:
        raise RuntimeError(_('Could not find staging repository: "%s"') % STAGING_NAME)

    # The data key can also contain a repository field, which will
    # trigger the creation functions to attempt to add the CV
    # to a new repo version and therefore break upload concurrency
    kwargs['data'].pop('repository')

    # kick off the upload and import task via the
    # pulp_ansible.app.serializers.CollectionVersionUploadSerializer serializer
    # Example structure:
    #   args: [ansible, CollectionVersionUploadSerializer]
    #   kwargs:
    #       repository_pk: <should be removed>
    #       data:
    #           sha256:
    #           artifact:
    #           repository: <should be removed>
    #       context:
    #           filename:
    #           filename_ns:
    general_create(*general_args, **kwargs)

    return repo


def import_to_staging(username, **kwargs):
    """Import collection version and move to staging repository.

    Custom task to call pulpcore's general_create() task then
    enqueue two tasks to add to staging repo.

    This task will not wait for the enqueued tasks to finish.
    """
    repo = _upload_collection(**kwargs)

    created_collection_versions = get_created_collection_versions()

    for collection_version in created_collection_versions:
        add = [collection_version.pk]
        ns = Namespace.objects.get(name=collection_version.namespace)
        if ns.last_created_pulp_metadata:
            add.append(ns.last_created_pulp_metadata.pk)
        dispatch(
            add_and_remove,
            exclusive_resources=[repo],
            kwargs=dict(
                add_content_units=add,
                repository_pk=repo.pk,
                remove_content_units=[],
            ),
        )

        if settings.GALAXY_ENABLE_API_ACCESS_LOG:
            _log_collection_upload(
                username,
                collection_version.namespace,
                collection_version.name,
                collection_version.version,
            )


def import_and_auto_approve(username, **kwargs):
    """Import collection version and automatically approve.

    Custom task to call pulpcore's general_create() task
    then automatically approve collection version so no
    manual approval action needs to occur.
    """

    # add the content to the staging repo.
    repo = _upload_collection(**kwargs)

    created_collection_versions = get_created_collection_versions()

    for collection_version in created_collection_versions:
        ns = Namespace.objects.get(name=collection_version.namespace)
        ns_pk = None
        if ns.last_created_pulp_metadata:
            ns_pk = ns.last_created_pulp_metadata.pk
        call_auto_approve_task(collection_version, repo, ns_pk)

        if settings.GALAXY_ENABLE_API_ACCESS_LOG:
            _log_collection_upload(
                username,
                collection_version.namespace,
                collection_version.name,
                collection_version.version,
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
