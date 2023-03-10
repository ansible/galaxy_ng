from django.conf import settings
from django.utils.translation import gettext_lazy as _

from pulpcore.plugin.tasking import add_and_remove, dispatch
from pulp_ansible.app.models import (
    CollectionVersion,
    CollectionVersionSignature,
    AnsibleCollectionDeprecated,
    CollectionVersionMark,
    AnsibleNamespaceMetadata,
    AnsibleRepository,
)
from pulp_ansible.app.tasks.signature import sign

from pulpcore.plugin.models import TaskGroup, SigningService


SIGNING_SERVICE_NAME = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE", "ansible-default")
AUTO_SIGN = settings.get("GALAXY_AUTO_SIGN_COLLECTIONS", False)


def auto_approve(src_repo_pk, cv_pk):
    published_repos = AnsibleRepository.objects.filter(pulp_labels__pipeline="approved")
    published_pks = list(published_repos.values_list("pk", flat=True))
    staging_repo = AnsibleRepository.objects.get(pk=src_repo_pk)

    add_and_remove(
        src_repo_pk,
        add_content_units=[cv_pk],
        remove_content_units=[],
    )

    try:
        signing_service = AUTO_SIGN and SigningService.objects.get(name=SIGNING_SERVICE_NAME)
    except SigningService.DoesNotExist:
        raise RuntimeError(_('Signing %s service not found') % SIGNING_SERVICE_NAME)

    # Sign the collection if auto sign is enabled
    if AUTO_SIGN:
        sign(
            repository_href=staging_repo,
            content_hrefs=[cv_pk],
            signing_service_href=signing_service.pk
        )

    # move the new collection (along with all it's associated objects) into
    # all of the approved repos.
    dispatch(
        move_collection,
        exclusive_resources=published_repos,
        shared_resources=[staging_repo],
        kwargs={
            "cv_pk": cv_pk,
            "src_repo_pk": staging_repo.pk,
            "dest_repo_list": published_pks,
        }
    )


def call_auto_approve_task(collection_version, repo):
    """
    Dispatches the auto approve task
    """
    task_group = TaskGroup.current()

    auto_approve_task = dispatch(
        auto_approve,
        exclusive_resources=[repo],
        task_group=task_group,
        kwargs=dict(
            cv_pk=collection_version.pk,
            src_repo_pk=repo.pk,
        ),
    )

    task_group.finish()

    return auto_approve_task


def call_move_content_task(collection_version, source_repo, dest_repo):
    """
    Dispatches the move collection task
    """

    return dispatch(
        move_collection,
        exclusive_resources=[source_repo, dest_repo],
        kwargs=dict(
            cv_pk=collection_version.pk,
            src_repo_pk=source_repo.pk,
            dest_repo_list=[dest_repo.pk],
        ),
    )


def copy_collection(cv_pk, src_repo_pk, dest_repo_list):
    """
    Copy a collection and all of it's contents into a list of destination repositories
    """
    src_repo = AnsibleRepository.objects.get(pk=src_repo_pk)
    collection_version = CollectionVersion.objects.get(pk=cv_pk)

    content_types = src_repo.content.values_list('pulp_type', flat=True).distinct()
    source_pks = src_repo.content.values_list("pk", flat=True)

    content = [cv_pk]

    # collection signatures
    if 'ansible.collection_signature' in content_types:
        signatures_pks = CollectionVersionSignature.objects.filter(
            signed_collection=cv_pk,
            pk__in=source_pks
        ).values_list("pk", flat=True)
        if signatures_pks:
            content.append(*signatures_pks)

    # collection version mark
    if 'ansible.collection_mark' in content_types:
        marks_pks = CollectionVersionMark.objects.filter(
            marked_collection=cv_pk,
            pk__in=source_pks
        ).values_list("pk", flat=True)
        if marks_pks:
            content.append(*marks_pks)

    # collection deprecation
    if 'ansible.collection_deprecation' in content_types:
        deprecations_pks = AnsibleCollectionDeprecated.objects.filter(
            pk__in=source_pks,
            namespace=collection_version.namespace,
            name=collection_version.name,
        ).values_list("pk", flat=True)
        if deprecations_pks:
            content.append(*deprecations_pks)

    namespaces_pks = AnsibleNamespaceMetadata.objects.filter(
        pk__in=source_pks,
        name=collection_version.namespace
    ).values_list("pk", flat=True)
    if namespaces_pks:
        content.append(*namespaces_pks)

    for pk in dest_repo_list:
        add_and_remove(
            repository_pk=pk,
            add_content_units=content,
            remove_content_units=[]
        )


def move_collection(cv_pk, src_repo_pk, dest_repo_list):
    copy_collection(cv_pk, src_repo_pk, dest_repo_list)

    # don't need to clean anything other than the collection version because everything
    # else will get handled by AnsibleRepository.finalize_repo_version()
    add_and_remove(
        repository_pk=src_repo_pk,
        add_content_units=[],
        remove_content_units=[cv_pk]
    )
