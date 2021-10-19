from subprocess import Popen, run, PIPE, STDOUT

from galaxy_ng.tests.functional.utils import TestCaseUsingBindings
from galaxy_ng.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


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
        pull_registry = "registry.access.redhat.com"

        # Pull images, record image id for cleanup
        proc = Popen(
            [container_engine, "pull", f"{pull_registry}/{image}:{tag}"],
            stdout=PIPE,
            stderr=STDOUT,
            encoding="utf-8",
        )
        image_id = ""
        for line in proc.stdout:
            image_id = line.strip()

        # Tag images
        run([container_engine, "tag", f"{pull_registry}/{image}:{tag}", f"{registry}/{image}:{tag}"],)

        # Push images to localhost:5001
        run([container_engine, "push", "--tls-verify=false", f"{registry}/{image}:{tag}"])

        return image_id

    def test_list_container_repository_tags(self):
        self.login_to_registry()

        image_ids = []
        image = "ubi8"
        tags = ["8.1", "8.2"]
        for tag in tags:
            image_id = self.create_container_repository(
                image=image,
                registry="localhost:5001",
                tag=tag)
            image_ids.append(image_id)

        response = self.container_repo_tags_api.list(base_path=image)

        self.assertEqual(response.meta.count, len(tags))
        for entry in response.data:
            self.assertIn(entry.name, tags)

        # Delete downloaded images
        for image_id in image_ids:
            run(['podman', "image", "rm", f"{image_id}", "--force"])

        # Delete Content Repository
        # self.container_repo_api.delete(base_path=image)
