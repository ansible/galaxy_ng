"""Tests that Collections can be uploaded to  Pulp with the ansible-galaxy CLI."""

import subprocess
import tempfile

from pulpcore.client.galaxy_ng import (
    ApiContentV3CollectionsApi,
    ApiV3NamespacesApi,
)
from pulp_smash import api, config
from pulp_smash.pulp3.bindings import delete_orphans, PulpTestCase
from pulp_smash.utils import http_get

from galaxy_ng.tests.functional.utils import gen_galaxy_client
from galaxy_ng.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class InstallCollectionTestCase(PulpTestCase):
    """Test whether ansible-galaxy can upload a Collection to Pulp."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = gen_galaxy_client()
        cls.smash_client = api.Client(cls.cfg, api.smart_handler)
        cls.namespace_api = ApiV3NamespacesApi(cls.client)
        cls.collections_api = ApiContentV3CollectionsApi(cls.client)
        token = cls.smash_client.post("/api/galaxy/v3/auth/token/")["token"]
        with open("ansible.cfg", "r") as f:
            cls.previous_ansible_cfg = f.read()
        ansible_cfg = (
            f"{cls.previous_ansible_cfg}\n"
            "[galaxy]\n"
            "server_list = community_repo\n"
            "\n"
            "[galaxy_server.community_repo]\n"
            f"url={ cls.cfg.get_content_host_base_url()}/api/galaxy/content/inbound-pulp/\n"
            f"token={token}"
        )
        with open("ansible.cfg", "w") as f:
            f.write(ansible_cfg)

    def tearDown(self):
        """Clean class-wide variable."""
        with open("ansible.cfg", "w") as f:
            f.write(self.previous_ansible_cfg)

    def test_upload_collection(self):
        """Test whether ansible-galaxy can upload a Collection to Pulp."""
        delete_orphans()

        data = str(self.namespace_api.list().data)
        if "pulp" not in data:
            self.namespace_api.create(namespace={"name": "pulp", "groups": []})

        with tempfile.TemporaryDirectory() as tmp_dir:
            content = http_get(
                "https://galaxy.ansible.com/download/pulp-squeezer-0.0.9.tar.gz"
            )
            collection_path = f"{tmp_dir}/pulp-squeezer-0.0.9.tar.gz"
            with open(collection_path, "wb") as f:
                f.write(content)

            cmd = "ansible-galaxy collection publish -vvv -c {}".format(collection_path)

            subprocess.run(cmd.split())

        collections = self.collections_api.list("published")
        self.assertEqual(collections.meta.count, 1)

        collection = self.collections_api.read(
            path="published", namespace="pulp", name="squeezer"
        )
        self.assertEqual(collection.namespace, "pulp")
        self.assertEqual(collection.name, "squeezer")
        self.assertEqual(collection.highest_version["version"], "0.0.9")
