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

If retain_repo_versions value has been manually set to greater than 1, than the
CollectionVersion will still exist in previous RepositoryVersion and will
not get deleted from system on orphan_cleanup. In the future if the Content no
longer exists in a RepositoryVersion (they have since been deleted), then the
subsequent orphan_cleanup will delete it from the system.
"""

import logging

from pulp_ansible.app.models import Collection, CollectionVersion
from pulp_container.app import tasks as pulp_container_tasks
from pulpcore.app.tasks import orphan_cleanup, reclaim_space
from pulpcore.plugin.tasking import add_and_remove, general_multi_delete

log = logging.getLogger(__name__)


def _remove_collection_version_from_repos(collection_version):
    """Remove CollectionVersion from latest RepositoryVersion of each repo."""
    for repo in collection_version.repositories.all():
        add_and_remove(repo.pk, add_content_units=[], remove_content_units=[collection_version.pk])
    collection_version.save()


def delete_collection_version(collection_version_pk):
    """Task to delete CollectionVersion object.

    Sequentially do the following in a single task:
    1. Call _remove_collection_version_from_repos
    2. Run orphan_cleanup to delete the CollectionVersion
    3. Delete Collection if it has no more CollectionVersion
    """

    collection_version = CollectionVersion.objects.get(pk=collection_version_pk)
    collection = collection_version.collection

    _remove_collection_version_from_repos(collection_version)

    log.info("Running orphan_cleanup to delete CollectionVersion object and artifact")
    orphan_cleanup(content_pks=None, orphan_protection_time=10)

    if not collection.versions.all():
        log.info("Collection has no more versions, deleting collection {}".format(collection))
        collection.delete()


def delete_collection(collection_pk):
    """Task to delete Collection object.

    Sequentially do the following in a single task:
    1. For each CollectionVersion call _remove_collection_version_from_repos
    2. Run orphan_cleanup to delete the CollectionVersions
    3. Delete Collection
    """

    collection = Collection.objects.get(pk=collection_pk)
    for version in collection.versions.all():
        _remove_collection_version_from_repos(version)

    log.info("Running orphan_cleanup to delete CollectionVersion objects and artifacts")
    orphan_cleanup(content_pks=None, orphan_protection_time=10)

    log.info("Deleting collection {}".format(collection))
    collection.delete()


def delete_container_distribution(instance_ids):
    """Deletes a container distribution and push repository related."""

    log.info("Running core.general_multi_delete to delete distro and repo")
    general_multi_delete(instance_ids=instance_ids)

    log.info("Running orphan_cleanup to delete Container objects and artifacts")
    orphan_cleanup(content_pks=None, orphan_protection_time=10)


def delete_container_image_manifest(repository_pk, content_unit_pks):
    """Deletes a container image manifest."""

    log.info(f"Running delete manifest for {repository_pk}")
    pulp_container_tasks.recursive_remove_content(
        repository_pk=repository_pk,
        content_units=content_unit_pks,
    )

    log.info(f"Reclaiming disk space for {repository_pk}")
    reclaim_space(repo_pks=[repository_pk], force=True)
