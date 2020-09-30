import logging
import pprint
from django.db.models import F, Q

from pulpcore.plugin.models import (
    CreatedResource,
    GroupProgressReport,
    ProgressReport,
    Task,
    TaskGroup,
)

from pulpcore.plugin.tasking import add_and_remove, enqueue_with_reservation

from pulp_ansible.app.models import (
    AnsibleRepository,
    CollectionVersion,
)

from galaxy_ng.app import models

log = logging.getLogger(__name__)
pf = pprint.pformat


def curate_all_synclist_repository(upstream_repository_name, **kwargs):
    """When upstream_repository has changed, update all synclists repos associated with it.

    The synclist repos will be updated to upstream_repository

    This will create a lot of curate_synclist_repository tasks.
    It will create a TaskGroup containing those tasks.

    If neccasary, it may create many TaskGroups.

    It may need to schedule a series of TaskGroups, potentially
    in order of priority.

    This task need to be cancelable."""

    upstream_repository = AnsibleRepository.objects.get(name=upstream_repository_name)
    synclist_qs = models.SyncList.objects.filter(upstream_repository=upstream_repository)

    task_group = TaskGroup.objects.create(
        description=f"Curating all synclists repos that curate from {upstream_repository_name}"
    )
    task_group.save()

    CreatedResource.objects.create(content_object=task_group)

    current_task = Task.current()
    current_task.task_group = task_group
    current_task.save()

    GroupProgressReport(
        message="Synclists curating upstream repo",
        code="synclist.curate",
        total=synclist_qs.count(),
        task_group=task_group,
    ).save()

    with ProgressReport(
        message="Synclists curating upstream repo task",
        code="synclist.curate.log",
        total=synclist_qs.count(),
    ) as task_progress_report:

        for synclist in synclist_qs:
            # TODO: filter down to just synclists that have a synclist repo
            # locks need to be Model or str not int
            locks = [str(synclist.id)]

            task_args = (synclist.id,)
            task_kwargs = {}

            enqueue_with_reservation(
                curate_synclist_repository,
                locks,
                args=task_args,
                kwargs=task_kwargs,
                task_group=task_group,
            )
            task_progress_report.increment()

            progress_report = task_group.group_progress_reports.filter(code="synclist.curate")
            progress_report.update(done=F("done") + 1)

    log.info(
        "Finishing curating %s synclist repos based on %s update",
        synclist_qs.count(),
        upstream_repository,
    )

    task_group.finish()


def curate_synclist_repository(synclist_pk, **kwargs):
    """Update a synclist repo based on it's policy and spec.

    Update a curated synclist repo to use the latest versions from
    upstream as specified by the synclist's policy and it's collections
    and namespaces fields.

    This is intended to work on one synclist and synclist repo at a time.
    """

    synclist = models.SyncList.objects.get(pk=synclist_pk)

    upstream_repository = synclist.upstream_repository
    latest_upstream = upstream_repository.latest_version()

    log.info(
        'Applying synclist "%s" with policy=%s to curate repo "%s" from upstream repo "%s"',
        synclist.name,
        synclist.policy,
        synclist.repository.name,
        upstream_repository.name,
    )

    locks = [synclist.repository]

    namespaces = synclist.namespaces.filter().values_list("name", flat=True)

    collection_versions = CollectionVersion.objects.filter(
        Q(
            repositories=synclist.upstream_repository,
            collection__namespace__in=namespaces,
            is_highest=True,
        )
        | Q(
            collection__in=synclist.collections.all(),
            repositories=synclist.repository,
            is_highest=True,
        )
    )

    if synclist.policy == "exclude":
        task_kwargs = {
            "base_version_pk": str(latest_upstream.pulp_id),
            "repository_pk": str(synclist.repository.pulp_id),
            "add_content_units": [],
            "remove_content_units": collection_versions,
        }

    elif synclist.policy == "include":
        task_kwargs = {
            "repository_pk": str(synclist.repository.pulp_id),
            "add_content_units": collection_versions,
            "remove_content_units": ["*"],
        }

    enqueue_with_reservation(
        add_and_remove, locks, kwargs=task_kwargs,
    )
