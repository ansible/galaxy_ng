"""Tests that verify download of content served by Pulp."""
import hashlib
import unittest
from random import choice
from urllib.parse import urljoin

from pulp_smash import config, utils
from pulp_smash.pulp3.utils import download_content_unit, gen_distribution, gen_repo

from galaxy_ng.tests.functional.constants import GALAXY_FIXTURE_URL
from galaxy_ng.tests.functional.utils import (
    gen_galaxy_client,
    get_galaxy_content_paths,
    gen_galaxy_remote,
    monitor_task,
)
from galaxy_ng.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


# Implement tests.functional.utils.get_galaxy_content_unit_paths(),
# as well as sync and publish support before enabling this test.
@unittest.skip("FIXME: plugin writer action required")
class DownloadContentTestCase(unittest.TestCase):
    """Verify whether content served by pulp can be downloaded."""

    def test_all(self):
        """Verify whether content served by pulp can be downloaded.

        The process of publishing content is more involved in Pulp 3 than it
        was under Pulp 2. Given a repository, the process is as follows:

        1. Create a publication from the repository. (The latest repository
           version is selected if no version is specified.) A publication is a
           repository version plus metadata.
        2. Create a distribution from the publication. The distribution defines
           at which URLs a publication is available, e.g.
           ``http://example.com/content/foo/`` and
           ``http://example.com/content/bar/``.

        Do the following:

        1. Create, populate, publish, and distribute a repository.
        2. Select a random content unit in the distribution. Download that
           content unit from Pulp, and verify that the content unit has the
           same checksum when fetched directly from Pulp-Fixtures.

        This test targets the following issues:

        * `Pulp #2895 <https://pulp.plan.io/issues/2895>`_
        * `Pulp Smash #872 <https://github.com/pulp/pulp-smash/issues/872>`_
        """
        cfg = config.get_config()
        client = gen_galaxy_client()
        repo_api = RepositoriesGalaxyApi(client)
        remote_api = RemotesGalaxyApi(client)
        publications = PublicationsGalaxyApi(client)
        distributions = DistributionsGalaxyApi(client)

        repo = repo_api.create(gen_repo())
        self.addCleanup(repo_api.delete, repo.pulp_href)

        body = gen_galaxy_remote()
        remote = remote_api.create(body)
        self.addCleanup(remote_api.delete, remote.pulp_href)

        # Sync a Repository
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        repo = repo_api.read(repo.pulp_href)

        # Create a publication.
        publish_data = GalaxyGalaxyPublication(repository=repo.pulp_href)
        publish_response = publications.create(publish_data)
        created_resources = monitor_task(publish_response.task)
        publication_href = created_resources[0]
        self.addCleanup(publications.delete, publication_href)

        # Create a distribution.
        body = gen_distribution()
        body["publication"] = publication_href
        distribution_response = distributions.create(body)
        created_resources = monitor_task(distribution_response.task)
        distribution = distributions.read(created_resources[0])
        self.addCleanup(distributions.delete, distribution.pulp_href)

        # Pick a content unit (of each type), and download it from both Pulp Fixtures…
        unit_paths = [choice(paths) for paths in get_galaxy_content_paths(repo.to_dict()).values()]
        fixtures_hashes = [
            hashlib.sha256(utils.http_get(urljoin(GALAXY_FIXTURE_URL, unit_path[0]))).hexdigest()
            for unit_path in unit_paths
        ]

        # …and Pulp.
        pulp_hashes = []
        cfg = config.get_config()
        for unit_path in unit_paths:
            content = download_content_unit(cfg, distribution.to_dict(), unit_path[1])
            pulp_hashes.append(hashlib.sha256(content).hexdigest())

        self.assertEqual(fixtures_hashes, pulp_hashes)
