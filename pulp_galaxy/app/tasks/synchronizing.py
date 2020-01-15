from gettext import gettext as _
import logging

from pulpcore.plugin.models import Artifact, ProgressReport, Remote, Repository
from pulpcore.plugin.stages import (
    DeclarativeArtifact,
    DeclarativeContent,
    DeclarativeVersion,
    Stage,
)

from pulp_galaxy.app.models import GalaxyContent, GalaxyRemote


log = logging.getLogger(__name__)


def synchronize(remote_pk, repository_pk, mirror):
    """
    Sync content from the remote repository.

    Create a new version of the repository that is synchronized with the remote.

    Args:
        remote_pk (str): The remote PK.
        repository_pk (str): The repository PK.
        mirror (bool): True for mirror mode, False for additive.

    Raises:
        ValueError: If the remote does not specify a URL to sync

    """
    remote = GalaxyRemote.objects.get(pk=remote_pk)
    repository = Repository.objects.get(pk=repository_pk)

    if not remote.url:
        raise ValueError(_("A remote must have a url specified to synchronize."))

    # Interpret policy to download Artifacts or not
    deferred_download = remote.policy != Remote.IMMEDIATE
    first_stage = GalaxyFirstStage(remote, deferred_download)
    DeclarativeVersion(first_stage, repository, mirror=mirror).create()


class GalaxyFirstStage(Stage):
    """
    The first stage of a pulp_galaxy sync pipeline.
    """

    def __init__(self, remote, deferred_download):
        """
        The first stage of a pulp_galaxy sync pipeline.

        Args:
            remote (FileRemote): The remote data to be used when syncing
            deferred_download (bool): if True the downloading will not happen now. If False, it will
                happen immediately.

        """
        super().__init__()
        self.remote = remote
        self.deferred_download = deferred_download

    async def run(self):
        """
        Build and emit `DeclarativeContent` from the Manifest data.

        Args:
            in_q (asyncio.Queue): Unused because the first stage doesn't read from an input queue.
            out_q (asyncio.Queue): The out_q to send `DeclarativeContent` objects to

        """
        downloader = self.remote.get_downloader(url=self.remote.url)
        result = await downloader.run()
        # Use ProgressReport to report progress
        for entry in self.read_my_metadata_file_somehow(result.path):
            unit = GalaxyContent(entry)  # make the content unit in memory-only
            artifact = Artifact(entry)  # make Artifact in memory-only
            da = DeclarativeArtifact(
                artifact,
                entry.url,
                entry.relative_path,
                self.remote,
                deferred_download=self.deferred_download,
            )
            dc = DeclarativeContent(content=unit, d_artifacts=[da])
            await self.put(dc)

    def read_my_metadata_file_somehow(self, path):
        """
        Parse the metadata for galaxy Content type.

        Args:
            path: Path to the metadata file
        """
        pass
