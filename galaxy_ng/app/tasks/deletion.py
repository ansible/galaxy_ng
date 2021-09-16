import logging

from pulp_ansible.app.models import CollectionVersion
from pulpcore.app.tasks import orphan_cleanup
from pulpcore.plugin.tasking import add_and_remove

log = logging.getLogger(__name__)


def _remove_collection_version_from_repos(collection_version):
    """Remove CollectionVersion from each repo, and ensure no old RepositoryVersion."""
    for repo in collection_version.repositories.all():
        # enforce retain_repo_versions is set to 1 on the repository
        if repo.retain_repo_versions != 1:
            repo.retain_repo_versions = 1
            repo.save()

        # remove CollectionVersion from latest RepositoryVersion
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
    orphan_cleanup(content_pks=None, orphan_protection_time=0)

    if not collection.versions.all():
        log.info("Collection has no more versions, deleting collection {}".format(collection))
        collection.delete()
