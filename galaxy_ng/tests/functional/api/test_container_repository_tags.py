import unittest

from urllib.parse import urlparse

from pulpcore.client.galaxy_ng.exceptions import ApiException
from pulp_container.tests.functional.api import rbac_base
from pulp_container.tests.functional.constants import PULP_FIXTURE_1
from pulp_smash import cli

from galaxy_ng.tests.functional.utils import TestCaseUsingBindings


class ContainerRepositoryTagsTestCase(TestCaseUsingBindings, rbac_base.BaseRegistryTest):
    """Test whether a container repository's tags can be listed.

    When running functional tests in dev environment please ensure that
    Pulp Smash can either execute commands as root or can successfully
    execute "sudo" on the localhost.
    .. note:: When running against a non-https registry the client config
        `insecure-registries` must be enabled.
    For docker it is located in `/etc/docker/daemon.json` and content is::
        {"insecure-registries": ["0.0.0.0:5001"]}
    For podman it is located in `/etc/containers/registries.conf` with::
        [registries.insecure]
        registries = ['0.0.0.0:5001']
    """

    @classmethod
    def setUpClass(cls):
        """
        Define APIs to use and pull images needed later in tests
        """
        super().setUpClass()

        cls.registry = cli.RegistryClient(cls.cfg)
        cls.registry.raise_if_unsupported(unittest.SkipTest, "Tests require podman/docker")
        cls.registry_name = urlparse(cls.cfg.get_base_url()).netloc
        admin_user, admin_password = cls.cfg.pulp_auth
        cls.user_admin = {"username": admin_user, "password": admin_password}
        cls._pull(f"{PULP_FIXTURE_1}:manifest_a")

    def test_list_container_repository_tags(self):
        image_name = "foo/bar"
        image_path = f"{PULP_FIXTURE_1}:manifest_a"
        local_url = "/".join([self.registry_name, f"{image_name}:1.0"])

        # expect the Container Repository Tags not to exist yet
        with self.assertRaises(ApiException) as context:
            self.container_repo_tags_api.list(base_path=image_name)

        # Bad request
        assert context.exception.status == 404

        self._push(image_path, local_url, self.user_admin)

        response = self.container_repo_tags_api.list(base_path=image_name)

        self.assertEqual(response.meta.count, 1)
        for entry in response.data:
            self.assertIn(entry.name, ["1.0"])

        # Delete created Execution Environment
        # api does not currently support delete
        ee_delete_response = self.smash_client.delete(
            f"{self.galaxy_api_prefix}/_ui/v1/execution-environments/repositories/{image_name}/"
        )
        print(f"Delete execution environment: {ee_delete_response['state']}")
