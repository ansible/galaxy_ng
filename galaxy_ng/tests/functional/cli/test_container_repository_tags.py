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
        cmds = [
            [container_engine, "pull", f"registry.access.redhat.com/{image}:{tag}"],
            [
                container_engine, "tag",
                f"registry.access.redhat.com/{image}:{tag}",
                f"{registry}/{image}:{tag}"
            ],
            [container_engine, "push", "--tls-verify=false", f"{registry}/{image}:{tag}"]
        ]
        for cmd in cmds:
            run(cmd)

    def delete_container_repository(self):
        pass

    def test_list_container_repository_tags(self):
        self.setUpClass()
        self.login_to_registry()

        image = "ubi8"
        tags = ["8.2", "8.3"]
        for tag in tags:
            self.create_container_repository(
                image=image,
                registry="localhost:5001",
                tag=tag)

        response = self.container_repo_tags_api.list(base_path=image)

        self.assertEqual(response.meta.count, len(tags))
        for entry in response.data:
            self.assertIn(entry.name, tags)
