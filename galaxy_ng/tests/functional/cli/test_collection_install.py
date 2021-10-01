"""Tests that Collections hosted by Pulp can be installed by ansible-galaxy."""
from os import path
import subprocess
import tempfile

from pulpcore.client.galaxy_ng import (
    ApiContentV3CollectionsApi,
    ApiContentV3SyncApi,
    ApiContentV3SyncConfigApi,
)
from pulp_smash import api, config
from pulp_smash.pulp3.bindings import monitor_task, PulpTestCase

from galaxy_ng.tests.functional.utils import gen_galaxy_client
from galaxy_ng.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class InstallCollectionTestCase(PulpTestCase):
    """Test whether ansible-galaxy can install a Collection hosted by Pulp."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = gen_galaxy_client()
        cls.smash_client = api.Client(cls.cfg, api.smart_handler)
        cls.collections_api = ApiContentV3CollectionsApi(cls.client)
        cls.sync_config_api = ApiContentV3SyncConfigApi(cls.client)
        cls.sync_api = ApiContentV3SyncApi(cls.client)
        token = cls.smash_client.post("/api/galaxy/v3/auth/token/")["token"]
        with open("ansible.cfg", "r") as f:
            cls.previous_ansible_cfg = f.read()
        ansible_cfg = (
            f"{cls.previous_ansible_cfg}\n"
            "[galaxy]\n"
            "server_list = community_repo\n"
            "\n"
            "[galaxy_server.community_repo]\n"
            f"url={ cls.cfg.get_content_host_base_url()}/api/galaxy/content/community/\n"
            f"token={token}"
        )
        with open("ansible.cfg", "w") as f:
            f.write(ansible_cfg)

    def tearDown(self):
        """Clean class-wide variable."""
        with open("ansible.cfg", "w") as f:
            f.write(self.previous_ansible_cfg)

    def create_install_scenario(self, collection_name):
        """Create Install scenario."""
        # Sync the repository.
        self.sync_config_api.update(
            "community",
            {
                "url": "https://galaxy.ansible.com/api/",
                "requirements_file": f"collections:\n  - {collection_name}",
            },
        )

        response = self.sync_api.sync("community")
        monitor_task(f"/pulp/api/v3/tasks/{response.task}/")

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
        self.create_install_scenario("ansible.posix")
