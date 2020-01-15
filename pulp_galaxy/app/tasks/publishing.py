import logging
from gettext import gettext as _

from pulpcore.plugin.models import (
    RepositoryVersion,
    PublishedArtifact,
    PublishedMetadata,
    RemoteArtifact,
)
from pulpcore.plugin.tasking import WorkingDirectory

from pulp_galaxy.app.models import GalaxyPublication


log = logging.getLogger(__name__)


def publish(repository_version_pk):
    """
    Create a Publication based on a RepositoryVersion.

    Args:
        repository_version_pk (str): Create a publication from this repository version.
    """
    repository_version = RepositoryVersion.objects.get(pk=repository_version_pk)

    log.info(
        _("Publishing: repository={repo}, version={ver}").format(
            repo=repository_version.repository.name, ver=repository_version.number,
        )
    )
    with WorkingDirectory():
        with GalaxyPublication.create(repository_version) as publication:
            # Write any Artifacts (files) to the file system, and the database.
            #
            # artifact = YourArtifactWriter.write(relative_path)
            # published_artifact = PublishedArtifact(
            #     relative_path=artifact.relative_path,
            #     publication=publication,
            #     content_artifact=artifact)
            # published_artifact.save()

            # Write any metadata files to the file system, and the database.
            #
            # metadata = YourMetadataWriter.write(relative_path)
            # metadata = PublishedMetadata(
            #     relative_path=os.path.basename(manifest.relative_path),
            #     publication=publication,
            #     file=File(open(manifest.relative_path, "rb")))
            # metadata.save()
            pass

    log.info(_("Publication: {publication} created").format(publication=publication.pk))
