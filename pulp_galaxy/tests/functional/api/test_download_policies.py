# coding=utf-8
"""Tests for Pulp`s download policies."""
import unittest

from pulp_smash import api, config
from pulp_smash.pulp3.utils import gen_repo, get_added_content_summary, get_content_summary, sync

from pulp_galaxy.tests.functional.constants import (
    GALAXY_FIXTURE_SUMMARY,
    GALAXY_REMOTE_PATH,
    GALAXY_REPO_PATH,
    DOWNLOAD_POLICIES,
)
from pulp_galaxy.tests.functional.utils import gen_galaxy_remote, skip_if
from pulp_galaxy.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


# Implement sync support before enabling this test.
@unittest.skip("FIXME: plugin writer action required")
class SyncDownloadPolicyTestCase(unittest.TestCase):
    """Sync a repository with different download policies.

    This test targets the following issue:

    `Pulp #4126 <https://pulp.plan.io/issues/4126>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)
        cls.DP_ON_DEMAND = "on_demand" in DOWNLOAD_POLICIES
        cls.DP_STREAMED = "streamed" in DOWNLOAD_POLICIES

    @skip_if(bool, "DP_ON_DEMAND", False)
    def test_on_demand(self):
        """Sync with ``on_demand`` download policy. See :meth:`do_test`."""
        self.do_test("on_demand")

    @skip_if(bool, "DP_STREAMED", False)
    def test_streamed(self):
        """Sync with ``streamend`` download policy.  See :meth:`do_test`."""
        self.do_test("streamed")

    def do_test(self, download_policy):
        """Sync repositories with the different ``download_policy``.

        Do the following:

        1. Create a repository, and a remote.
        2. Assert that repository version is None.
        3. Sync the remote.
        4. Assert that repository version is not None.
        5. Assert that the correct number of possible units to be downloaded
           were shown.
        6. Sync the remote one more time in order to create another repository
           version.
        7. Assert that repository version is different from the previous one.
        8. Assert that the same number of units are shown, and after the
           second sync no extra units should be shown, since the same remote
           was synced again.
        """
        repo = self.client.post(GALAXY_REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["pulp_href"])

        body = gen_galaxy_remote(**{"policy": download_policy})
        remote = self.client.post(GALAXY_REMOTE_PATH, body)
        self.addCleanup(self.client.delete, remote["pulp_href"])

        # Sync the repository.
        self.assertEqual(repo["latest_version_href"], f"{repo['pulp_href']}versions/0/")
        sync(self.cfg, remote, repo)
        repo = self.client.get(repo["pulp_href"])

        self.assertIsNotNone(repo["latest_version_href"])
        self.assertDictEqual(get_content_summary(repo), GALAXY_FIXTURE_SUMMARY)
        self.assertDictEqual(get_added_content_summary(repo), GALAXY_FIXTURE_SUMMARY)

        # Sync the repository again.
        latest_version_href = repo["latest_version_href"]
        sync(self.cfg, remote, repo)
        repo = self.client.get(repo["pulp_href"])

        self.assertNotEqual(latest_version_href, repo["latest_version_href"])
        self.assertDictEqual(get_content_summary(repo), GALAXY_FIXTURE_SUMMARY)
        self.assertDictEqual(get_added_content_summary(repo), {})
