# coding=utf-8
"""Tests that verify download of content served by Pulp."""
import hashlib
import unittest
from random import choice
from urllib.parse import urljoin

from pulp_smash import api, config, utils
from pulp_smash.pulp3.utils import download_content_unit, gen_distribution, gen_repo, sync

from pulp_galaxy.tests.functional.constants import (
    GALAXY_DISTRIBUTION_PATH,
    GALAXY_FIXTURE_URL,
    GALAXY_PUBLICATION_PATH,
    GALAXY_REMOTE_PATH,
    GALAXY_REPO_PATH,
)
from pulp_galaxy.tests.functional.utils import (
    publish,
    gen_galaxy_remote,
    get_galaxy_content_paths,
)
from pulp_galaxy.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


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
        client = api.Client(cfg, api.json_handler)

        repo = client.post(GALAXY_REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo["pulp_href"])

        body = gen_galaxy_remote()
        remote = client.post(GALAXY_REMOTE_PATH, body)
        self.addCleanup(client.delete, remote["pulp_href"])

        sync(cfg, remote, repo)
        repo = client.get(repo["pulp_href"])

        # Create a publication.
        publication = publish(cfg, repo)
        self.addCleanup(client.delete, publication["pulp_href"])

        # Create a distribution.
        body = gen_distribution()
        body["publication"] = publication["pulp_href"]
        distribution = client.using_handler(api.task_handler).post(GALAXY_DISTRIBUTION_PATH, body)
        self.addCleanup(client.delete, distribution["pulp_href"])

        # Pick a content unit (of each type), and download it from both Pulp Fixtures…
        unit_paths = [choice(paths) for paths in get_galaxy_content_paths(repo).values()]
        fixtures_hashes = [
            hashlib.sha256(utils.http_get(urljoin(GALAXY_FIXTURE_URL, unit_path[0]))).hexdigest()
            for unit_path in unit_paths
        ]

        # …and Pulp.
        pulp_hashes = []
        for unit_path in unit_paths:
            content = download_content_unit(cfg, distribution, unit_path[1])
            pulp_hash.append(hashlib.sha256(content).hexdigest())

        self.assertEqual(fixtures_hashes, pulp_hashes)
