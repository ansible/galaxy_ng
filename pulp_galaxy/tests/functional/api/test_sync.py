# coding=utf-8
"""Tests that sync galaxy plugin repositories."""
import unittest

from pulp_smash import api, cli, config
from pulp_smash.exceptions import TaskReportError
from pulp_smash.pulp3.constants import MEDIA_PATH
from pulp_smash.pulp3.utils import gen_repo, get_added_content_summary, get_content_summary, sync

from pulp_galaxy.tests.functional.constants import (
    GALAXY_FIXTURE_SUMMARY,
    GALAXY_INVALID_FIXTURE_URL,
    GALAXY_REMOTE_PATH,
    GALAXY_REPO_PATH,
)
from pulp_galaxy.tests.functional.utils import gen_galaxy_remote
from pulp_galaxy.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


# Implement sync support before enabling this test.
@unittest.skip("FIXME: plugin writer action required")
class BasicSyncTestCase(unittest.TestCase):
    """Sync a repository with the galaxy plugin."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)

    def test_sync(self):
        """Sync repositories with the galaxy plugin.

        In order to sync a repository a remote has to be associated within
        this repository. When a repository is created this version field is set
        as None. After a sync the repository version is updated.

        Do the following:

        1. Create a repository, and a remote.
        2. Assert that repository version is None.
        3. Sync the remote.
        4. Assert that repository version is not None.
        5. Assert that the correct number of units were added and are present
           in the repo.
        6. Sync the remote one more time.
        7. Assert that repository version is different from the previous one.
        8. Assert that the same number of are present and that no units were
           added.
        """
        repo = self.client.post(GALAXY_REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["pulp_href"])

        body = gen_galaxy_remote()
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

        self.assertEqual(latest_version_href, repo["latest_version_href"])
        self.assertDictEqual(get_content_summary(repo), GALAXY_FIXTURE_SUMMARY)

    # This test may not make sense for all plugins, but is likely to be useful
    # for most. Check that it makes sense for yours before enabling it.
    @unittest.skip("FIXME: plugin writer action required")
    def test_file_decriptors(self):
        """Test whether file descriptors are closed properly.

        This test targets the following issue:

        `Pulp #4073 <https://pulp.plan.io/issues/4073>`_

        Do the following:

        1. Check if 'lsof' is installed. If it is not, skip this test.
        2. Create and sync a repo.
        3. Run the 'lsof' command to verify that files in the
           path ``/var/lib/pulp/`` are closed after the sync.
        4. Assert that issued command returns `0` opened files.
        """
        cli_client = cli.Client(self.cfg, cli.echo_handler)

        # check if 'lsof' is available
        if cli_client.run(("which", "lsof")).returncode != 0:
            raise unittest.SkipTest("lsof package is not present")

        repo = self.client.post(GALAXY_REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["pulp_href"])

        remote = self.client.post(GALAXY_REMOTE_PATH, gen_galaxy_remote())
        self.addCleanup(self.client.delete, remote["pulp_href"])

        sync(self.cfg, remote, repo)

        cmd = "lsof -t +D {}".format(MEDIA_PATH).split()
        response = cli_client.run(cmd).stdout
        self.assertEqual(len(response), 0, response)


# Implement sync support before enabling this test.
@unittest.skip("FIXME: plugin writer action required")
class SyncInvalidTestCase(unittest.TestCase):
    """Sync a repository with a given url on the remote."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)

    def test_invalid_url(self):
        """Sync a repository using a remote url that does not exist.

        Test that we get a task failure. See :meth:`do_test`.
        """
        context = self.do_test("http://i-am-an-invalid-url.com/invalid/")
        self.assertIsNotNone(context.exception.task["error"]["description"])

    # Provide an invalid repository and specify keywords in the anticipated error message
    @unittest.skip("FIXME: Plugin writer action required.")
    def test_invalid_galaxy_content(self):
        """Sync a repository using an invalid plugin_content repository.

        Assert that an exception is raised, and that error message has
        keywords related to the reason of the failure. See :meth:`do_test`.
        """
        context = self.do_test(GALAXY_INVALID_FIXTURE_URL)
        for key in ("mismached", "empty"):
            self.assertIn(key, context.exception.task["error"]["description"])

    def do_test(self, url):
        """Sync a repository given ``url`` on the remote."""
        repo = self.client.post(GALAXY_REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["pulp_href"])

        body = gen_galaxy_remote(url=url)
        remote = self.client.post(GALAXY_REMOTE_PATH, body)
        self.addCleanup(self.client.delete, remote["pulp_href"])

        with self.assertRaises(TaskReportError) as context:
            sync(self.cfg, remote, repo)
        return context
