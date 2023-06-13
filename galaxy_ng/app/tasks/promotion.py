from django.conf import settings

from pulpcore.plugin.tasking import add_and_remove, dispatch
from pulp_ansible.app.models import AnsibleRepository
from pulp_ansible.app.tasks.signature import sign
from pulp_ansible.app.tasks.copy import move_collection

from pulpcore.plugin.models import TaskGroup, SigningService


SIGNING_SERVICE_NAME = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE", "ansible-default")
AUTO_SIGN = settings.get("GALAXY_AUTO_SIGN_COLLECTIONS", False)


def auto_approve(src_repo_pk, cv_pk, ns_pk=None):
    published_repos = AnsibleRepository.objects.filter(pulp_labels__pipeline="approved")
    published_pks = list(published_repos.values_list("pk", flat=True))

    staging_repos = AnsibleRepository.objects.filter(pulp_labels__pipeline="staging")
    staging_pks = list(staging_repos.values_list("pk", flat=True))

    source_repo = AnsibleRepository.objects.get(pk=src_repo_pk)

    add = [cv_pk]
    if ns_pk:
        add.append(ns_pk)

    add_and_remove(
        src_repo_pk,
        add_content_units=add,
        remove_content_units=[],
    )

    try:
        signing_service = AUTO_SIGN and SigningService.objects.get(name=SIGNING_SERVICE_NAME)
    except SigningService.DoesNotExist:
        raise RuntimeError('Signing %s service not found' % SIGNING_SERVICE_NAME)

    # Sign the collection if auto sign is enabled
    if AUTO_SIGN:
        sign(
            repository_href=source_repo,
            content_hrefs=[cv_pk],
            signing_service_href=signing_service.pk
        )

    # if source repo isn't staging, don't move it to published repos
    if source_repo.pk in staging_pks:
        # move the new collection (along with all it's associated objects) into
        # all of the approved repos.
        dispatch(
            move_collection,
            exclusive_resources=published_repos,
            shared_resources=[source_repo],
            kwargs={
                "cv_pk_list": [cv_pk],
                "src_repo_pk": source_repo.pk,
                "dest_repo_list": published_pks,
            }
        )


def call_auto_approve_task(collection_version, repo, ns_pk):
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
            ns_pk=ns_pk,
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
            cv_pk_list=[collection_version.pk],
            src_repo_pk=source_repo.pk,
            dest_repo_list=[dest_repo.pk],
        ),
    )
