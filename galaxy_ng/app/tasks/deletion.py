import logging

from pulp_ansible.app.models import Collection, CollectionVersion
from pulp_container.app import tasks as pulp_container_tasks
from pulpcore.app.tasks import orphan_cleanup, reclaim_space
from pulpcore.plugin.tasking import add_and_remove

log = logging.getLogger(__name__)


def _cleanup_old_versions(repo):
    """Delete all the old versions of the given repository."""
    for version in repo.versions.complete().order_by("-number")[1:]:
        version.delete()


def _remove_collection_version_from_repos(collection_version):
    """Remove CollectionVersion from each repo, and ensure no old RepositoryVersion."""
    for repo in collection_version.repositories.all():
        # enforce retain_repo_versions is set to 1 on the repository
        if repo.retain_repo_versions != 1:
            repo.retain_repo_versions = 1
            repo.save()

        # remove CollectionVersion from latest RepositoryVersion
        add_and_remove(repo.pk, add_content_units=[], remove_content_units=[collection_version.pk])
        _cleanup_old_versions(repo)
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
    orphan_cleanup(content_pks=[collection_version.pk], orphan_protection_time=0)

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
    version_pks = []
    for version in collection.versions.all():
        _remove_collection_version_from_repos(version)
        version_pks.append(version.pk)

    log.info("Running orphan_cleanup to delete CollectionVersion objects and artifacts")
    orphan_cleanup(content_pks=version_pks, orphan_protection_time=0)

    log.info("Deleting collection {}".format(collection))
    collection.delete()


def delete_container_distribution(instance_ids):
    """Deletes a container distribution and push repository related."""

    log.info("Running container.general_multi_delete to delete distro and repo")
    pulp_container_tasks.general_multi_delete(instance_ids=instance_ids)

    log.info("Running orphan_cleanup to delete Container objects and artifacts")
    orphan_cleanup(content_pks=None, orphan_protection_time=10)


def delete_container_image_manifest(repository_pk, content_unit_pks, repo_latest_version_pk):
    """Deletes a container image manifest."""

    log.info(f"Running delete manifest for {repository_pk}")
    pulp_container_tasks.recursive_remove_content(
        repository_pk=repository_pk,
        content_units=content_unit_pks,
    )

    log.info(f"Reclaiming disk space for {repository_pk}")
    reclaim_space(repo_pks=[repository_pk], keeplist_rv_pks=[repo_latest_version_pk], force=True)
