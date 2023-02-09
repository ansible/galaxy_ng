"""tasks/deletion.py

This module includes tasks related to deleting Content.

You can remove Content from a Repository by making a new RepositoryVersion
without the Content. If an API endpoint uses a Distribution which points to
the latest_version of the Repository then the Content is unavailable,
however it is not deleted.

Content can only be deleted if it exists in no RepositoryVersion.

Content cannot be removed from a RepositoryVersion since it is immutable.

Pulp's orphan_cleanup task deletes any Content not part of a RepositoryVersion.

Deleting Content is made possible by retaining only one RepositoryVersion
for a Repository, and deleting all older RepositoryVersion. This module
assumes retain_repo_versions is set to 1 for all Repository the Content is
associated with.
"""

import logging
from django.db.models import Count
from pulp_container.app import tasks as pulp_container_tasks
from pulpcore.app.tasks import orphan_cleanup, reclaim_space
from pulpcore.plugin.tasking import general_multi_delete
from pulpcore.plugin.models import RepositoryContent

log = logging.getLogger(__name__)


def delete_container_distribution(instance_ids):
    """Deletes a container distribution and push repository related."""

    repository_ids = [item[0] for item in instance_ids]
    repository_content_pks = RepositoryContent.objects.annotate(
        num_repos=Count("repository")).filter(
        repository__pk__in=repository_ids, num_repos=1).values_list("content__pk", flat=True)

    log.info("Running core.general_multi_delete to delete distro and repo")
    general_multi_delete(instance_ids=instance_ids)

    log.info("Running orphan_cleanup to delete Container objects and artifacts")
    orphan_cleanup(content_pks=repository_content_pks, orphan_protection_time=0)


def delete_container_image_manifest(repository_pk, content_unit_pks, repo_latest_version_pk):
    """Deletes a container image manifest."""

    log.info(f"Running delete manifest for {repository_pk}")
    pulp_container_tasks.recursive_remove_content(
        repository_pk=repository_pk,
        content_units=content_unit_pks,
    )

    log.info(f"Reclaiming disk space for {repository_pk}")
    reclaim_space(repo_pks=[repository_pk], keeplist_rv_pks=[repo_latest_version_pk], force=True)
