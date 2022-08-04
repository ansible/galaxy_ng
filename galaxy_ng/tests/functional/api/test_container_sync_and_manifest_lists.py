from pulp_smash.pulp3.bindings import monitor_task

from galaxy_ng.tests.functional.utils import TestCaseUsingBindings


class ContainerSyncandManifestListTestCase(TestCaseUsingBindings):
    """Test container sync and manifest lists.

    At the moment, the only way to get a container with a manifest list is to sync it from another
    registy. Because of that, this will test both here.

    Test manifest list + sync
    - set up docker registry
    - set up remote container in docker registry for pulp/test-fixture-1
        - set tags to: ml_i, manifest_a
    - perform sync
    - verify that the repo has two images with tags ml_i and manifest_a,
      that manifest_a is a manifest and that ml_i is a manifest list with
      two manifests in it

    Test multiple repositories in a registry
    - set up remote container in docker registry for pulp/test-fixture-1 with just tag manifest_a
    - set up remote container in docker registry for pulp/test-fixture-1 with just tag manifest_b
    - sync the entire registry
        - verify that both repos have synced
    """

    def setUp(self):
        self.docker_registry = self.container_registries_api.create({
            "name": "Docker Hub",
            "url": "https://registry.hub.docker.com",
        })
        self.addCleanup(
            self.smash_client.delete,
            (
                f"{self.galaxy_api_prefix}/_ui/v1/execution-environments/"
                f"registries/{self.docker_registry.pk}/"
            )
        )

    def _delete_remote_repo(self, remote):
        self.smash_client.delete((
            f"{self.galaxy_api_prefix}/_ui/v1/execution-environments/"
            f"repositories/{remote.name}/"))

    def test_manifests_and_remote_sync(self):
        remote_repo = self.container_remotes_api.create({
            "name": "test-repo1",
            "upstream_name": "pulp/test-fixture-1",
            "include_tags": ["ml_i", "manifest_b"],
            "registry": self.docker_registry.pk,
        })

        self.addCleanup(self._delete_remote_repo, remote_repo)

        # the galaxy_ng client doesn't seem to return anything with the sync function, so we're
        # using the api directly instead
        self.smash_client.post((
            f"{self.galaxy_api_prefix}/_ui/v1/execution-environments/"
            f"repositories/{remote_repo.name}/_content/sync/"))

        tags_list = self.container_repo_tags_api.list(remote_repo.name)
        self.assertEqual(tags_list.meta.count, 2)

        tags_list = self.container_repo_tags_api.list(remote_repo.name, name="manifest_b")
        self.assertEqual(tags_list.meta.count, 1)

        tagged_ml = tags_list.data[0]
        self.assertIn("manifest.v2", tagged_ml.tagged_manifest.media_type)

        # Note, the manifest_a tag in the pulp test repo points to a
        # manifest that's part of the ml_i manifest list
        # so it won't show up in here since exclude_child_manifests
        # filters out any manifest that is part of a manifest list.
        image_list = self.container_images_api.list(remote_repo.name, exclude_child_manifests=True)
        self.assertEqual(image_list.meta.count, 1)

        manifest_list = image_list.data[0]

        self.assertEqual(len(manifest_list.image_manifests), 2)
        for img in manifest_list.image_manifests:
            self.assertEqual(img.architecture, "amd64")

        self.assertIn("manifest.list.v2", manifest_list.media_type)

    def test_registry_sync(self):
        remote_repo1 = self.container_remotes_api.create({
            "name": "test-repo1",
            "upstream_name": "pulp/test-fixture-1",
            "include_tags": ["manifest_b"],
            "registry": self.docker_registry.pk,
        })

        remote_repo2 = self.container_remotes_api.create({
            "name": "test-repo2",
            "upstream_name": "pulp/test-fixture-1",
            "include_tags": ["manifest_b"],
            "registry": self.docker_registry.pk,
        })

        self.addCleanup(self._delete_remote_repo, remote_repo1)
        self.addCleanup(self._delete_remote_repo, remote_repo2)

        sync_task = self.smash_client.post((
            f"{self.galaxy_api_prefix}/_ui/v1/execution-environments/"
            f"registries/{self.docker_registry.pk}/sync/"))

        for task in sync_task['child_tasks']:
            monitor_task(task)

        tags_list = self.container_repo_tags_api.list(remote_repo1.name)
        self.assertEqual(tags_list.meta.count, 1)

        tags_list = self.container_repo_tags_api.list(remote_repo2.name)
        self.assertEqual(tags_list.meta.count, 1)
