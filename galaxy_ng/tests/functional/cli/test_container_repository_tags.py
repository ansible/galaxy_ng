from subprocess import run

from galaxy_ng.tests.functional.utils import TestCaseUsingBindings
from galaxy_ng.tests.functional.utils import set_up_module as setUpModule  # noqa:F401

###
# 1. login to registry
#   - move to utils.py?
# 2. tag and push images
#   - move to utils.py?
# 3. verify tags via api endpoint
# 4. delete tags/images
#   - move to utils.py?
# 5. verify tags removed via api endpoint
#


class ContainerRepositoryTagsTestCase(TestCaseUsingBindings):
    """Test whether a container repository's tags can be listed."""

    @staticmethod
    def login_to_registry(
        container_engine="podman",
        user="admin",
        password="admin",
        registry="localhost:5001"
    ):
        """Login to a registry
        :param String container_engine: Container engine to be used, defaults to podman
        :param String user: User to login as
        :param String password: Password for User
        :param String registry: Registry to login to, ie: localhost:5001
        """
        cmd = [
            container_engine,
            "login", "-u", user, "-p", password,
            "--tls-verify=false",
            registry
        ]
        run(cmd)

    @staticmethod
    def create_container_repository(
        image,
        registry,
        container_engine="podman",
        tag="latest",
    ):
        """Create a container repository with a tagged image.
        :param String container_engine: Container engine to be used, defaults to podman
        :param String image: Image to pulled, tagged and pushed to the registry
        :param String tag: Optional tag for the image.  Defaults to 'latest'
        :param String registry: Registry to login to, ie: localhost:5001
        """
        cmds = [
            [container_engine, "pull", f"registry.access.redhat.com/{image}:{tag}"],
            [
                container_engine, "tag",
                f"registry.access.redhat.com/{image}:{tag}",
                f"{registry}/test-{image}:{tag}"
            ],
            [container_engine, "push", "--tls-verify=false", f"{registry}/{image}:{tag}"]
        ]
        for cmd in cmds:
            run(cmd)

    def delete_container_repository(self):
        pass

    def test_list_container_repository_tags(self):
        self.setUpClass()
        self.login_to_registry(password='password', registry='localhost')

        image = "ubi8"
        tags = ["8.2", "8.3"]
        for tag in tags:
            self.create_container_repository(
                image=image,
                registry="localhost",
                tag=tag)

        api_url = f"/_ui/v1/execution-environments/repositories/{image}/_content/tags/"
        response = self.smash_client.get(
            f"{self.galaxy_api_prefix}{api_url}"
        )
        print(response["data"][1])
        print(response["data"][1]["name"])
        self.assertEqual(response["meta"]["count"], len(tags))
        self.assertIn(response["data"][0]["name"], tags)
        self.assertIn(response["data"][1]["name"], tags)
