"""Tests that Collections hosted by Pulp can be installed by ansible-galaxy."""
from os import path
import subprocess
import tempfile
import pytest

from galaxy_ng.tests.functional.utils import TestCaseUsingBindings
from galaxy_ng.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class InstallCollectionTestCase(TestCaseUsingBindings):
    """Test whether ansible-galaxy can install a Collection hosted by Pulp."""

    def install_collection(self, collection_name, auth=True, repo_name="community"):
        """Install given collection."""

        # Preapare ansible.cfg for ansible-galaxy CLI
        self.update_ansible_cfg(repo_name, auth)

        # In a temp dir, install a collection using ansible-galaxy CLI
        with tempfile.TemporaryDirectory() as temp_dir:
            cmd = "ansible-galaxy collection install -vvv {} -c -p {}".format(
                collection_name, temp_dir
            )

            directory = "{}/ansible_collections/{}".format(
                temp_dir, collection_name.replace(".", "/")
            )

            self.assertTrue(
                not path.exists(directory), "Directory {} already exists".format(directory)
            )

            subprocess.run(cmd.split())

            self.assertTrue(path.exists(directory), "Could not find directory {}".format(directory))

    def test_install_collection(self):
        """Test whether ansible-galaxy can install a Collection hosted by Pulp."""
        collection_name = "ansible.posix"
        # Sync the repository.
        self.sync_repo(f"collections:\n  - {collection_name}")
        self.install_collection(collection_name)

    def test_install_collection_unauthenticated(self):
        """Test whether ansible-galaxy can download a Collection without auth."""

        pytest.skip(
            "GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD is not configurable yet.")

        collection_name = "ansible.posix"
        # Sync the repository.
        self.sync_repo(f"collections:\n  - {collection_name}")
        self.install_collection(collection_name, auth=False)
