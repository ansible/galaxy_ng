"""Utilities for tests for the galaxy plugin."""
import os
from functools import partial
import requests
from unittest import SkipTest
from tempfile import NamedTemporaryFile

from pulp_smash import api, config, selectors
from pulp_smash.pulp3.bindings import delete_orphans, monitor_task, PulpTestCase
from pulp_smash.pulp3.utils import (
    gen_remote,
    gen_repo,
    get_content,
    require_pulp_3,
    require_pulp_plugins,
    sync,
)

from galaxy_ng.tests.functional.constants import (
    GALAXY_CONTENT_NAME,
    GALAXY_CONTENT_PATH,
    GALAXY_FIXTURE_URL,
    GALAXY_PUBLICATION_PATH,
    GALAXY_REMOTE_PATH,
    GALAXY_REPO_PATH,
    GALAXY_URL,
)

from pulpcore.client.pulpcore import (
    ApiClient as CoreApiClient,
    ArtifactsApi,
    TasksApi,
)
from pulpcore.client.galaxy_ng import (
    ApiClient as GalaxyApiClient,
    ApiContentV3SyncApi,
    ApiContentV3SyncConfigApi,
    ApiV3NamespacesApi,
    ApiUiV1ExecutionEnvironmentsRepositoriesContentTagsApi as ContainerRepositoryEndpointApi,
    ApiUiV1ExecutionEnvironmentsRepositoriesApi as ContainerRepositoryApi,
    ApiUiV1ExecutionEnvironmentsRemotesApi,
    ApiUiV1ExecutionEnvironmentsRegistriesApi,
    ApiUiV1ExecutionEnvironmentsRepositoriesContentSyncApi,
    ApiUiV1ExecutionEnvironmentsRegistriesSyncApi,
    ApiUiV1ExecutionEnvironmentsRepositoriesContentImagesApi as ContainerImagesAPI,
)
from pulpcore.client.pulp_ansible import (
    ApiClient as PulpAnsibleApiClient,
    PulpAnsibleApiV3CollectionsApi,
)

configuration = config.get_config().get_bindings_config()


def set_up_module():
    """Skip tests Pulp 3 isn't under test or if galaxy_ng isn't installed."""
    require_pulp_3(SkipTest)
    require_pulp_plugins({"galaxy"}, SkipTest)


def gen_galaxy_client():
    """Return an OBJECT for galaxy client."""
    return GalaxyApiClient(configuration)


def gen_pulp_ansible_client():
    """Return an OBJECT for galaxy client."""
    return PulpAnsibleApiClient(configuration)


def gen_galaxy_remote(url=GALAXY_FIXTURE_URL, **kwargs):
    """Return a semi-random dict for use in creating a galaxy Remote.

    :param url: The URL of an external content source.
    """
    # FIXME: Add any fields specific to a galaxy remote here
    return gen_remote(url, **kwargs)


def get_galaxy_content_paths(repo, version_href=None):
    """Return the relative path of content units present in a galaxy repository.

    :param repo: A dict of information about the repository.
    :param version_href: The repository version to read.
    :returns: A dict of lists with the paths of units present in a given repository.
        Paths are given as pairs with the remote and the local version for different content types.
    """
    # FIXME: The "relative_path" is actually a file path and name
    # It's just an example -- this needs to be replaced with an implementation that works
    # for repositories of this content type.
    return {
        GALAXY_CONTENT_NAME: [
            (content_unit["relative_path"], content_unit["relative_path"])
            for content_unit in get_content(repo, version_href)[GALAXY_CONTENT_NAME]
        ],
    }


def gen_galaxy_content_attrs(artifact):
    """Generate a dict with content unit attributes.

    :param artifact: A dict of info about the artifact.
    :returns: A semi-random dict for use in creating a content unit.
    """
    # FIXME: Add content specific metadata here.
    return {"_artifact": artifact["pulp_href"]}


def populate_pulp(cfg, url=GALAXY_FIXTURE_URL):
    """Add galaxy contents to Pulp.

    :param pulp_smash.config.PulpSmashConfig: Information about a Pulp application.
    :param url: The galaxy repository URL. Defaults to
        :data:`pulp_smash.constants.GALAXY_FIXTURE_URL`
    :returns: A list of dicts, where each dict describes one galaxy content in Pulp.
    """
    client = api.Client(cfg, api.json_handler)
    remote = {}
    repo = {}
    try:
        remote.update(client.post(GALAXY_REMOTE_PATH, gen_galaxy_remote(url)))
        repo.update(client.post(GALAXY_REPO_PATH, gen_repo()))
        sync(cfg, remote, repo)
    finally:
        if remote:
            client.delete(remote["pulp_href"])
        if repo:
            client.delete(repo["pulp_href"])
    return client.get(GALAXY_CONTENT_PATH)["results"]


def publish(cfg, repo, version_href=None):
    """Publish a repository.
    :param pulp_smash.config.PulpSmashConfig cfg: Information about the Pulp
        host.
    :param repo: A dict of information about the repository.
    :param version_href: A href for the repo version to be published.
    :returns: A publication. A dict of information about the just created
        publication.
    """
    if version_href:
        body = {"repository_version": version_href}
    else:
        body = {"repository": repo["pulp_href"]}

    client = api.Client(cfg, api.json_handler)
    call_report = client.post(GALAXY_PUBLICATION_PATH, body)
    tasks = tuple(api.poll_spawned_tasks(cfg, call_report))
    return client.get(tasks[-1]["created_resources"][0])


skip_if = partial(selectors.skip_if, exc=SkipTest)  # pylint:disable=invalid-name
"""The ``@skip_if`` decorator, customized for unittest.

:func:`pulp_smash.selectors.skip_if` is test runner agnostic. This function is
identical, except that ``exc`` has been set to ``unittest.SkipTest``.
"""

core_client = CoreApiClient(configuration)
tasks = TasksApi(core_client)


def gen_artifact(url=GALAXY_URL):
    """Creates an artifact."""
    response = requests.get(url)
    with NamedTemporaryFile() as temp_file:
        temp_file.write(response.content)
        temp_file.flush()
        artifact = ArtifactsApi(core_client).create(file=temp_file.name)
        return artifact.to_dict()


class TestCaseUsingBindings(PulpTestCase):
    """A parent TestCase that instantiates the various bindings used throughout tests."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = gen_galaxy_client()
        cls.pulp_ansible_client = gen_pulp_ansible_client()
        cls.smash_client = api.Client(cls.cfg, api.smart_handler)
        cls.namespace_api = ApiV3NamespacesApi(cls.client)
        cls.collections_api = PulpAnsibleApiV3CollectionsApi(cls.pulp_ansible_client)
        cls.sync_config_api = ApiContentV3SyncConfigApi(cls.client)
        cls.sync_api = ApiContentV3SyncApi(cls.client)
        cls.container_repo_tags_api = ContainerRepositoryEndpointApi(cls.client)
        cls.container_repo_api = ContainerRepositoryApi(cls.client)
        cls.container_remotes_api = ApiUiV1ExecutionEnvironmentsRemotesApi(cls.client)
        cls.container_registries_api = ApiUiV1ExecutionEnvironmentsRegistriesApi(cls.client)
        cls.container_remote_sync_api = \
            ApiUiV1ExecutionEnvironmentsRepositoriesContentSyncApi(cls.client)
        cls.container_registry_sync_api = ApiUiV1ExecutionEnvironmentsRegistriesSyncApi(cls.client)
        cls.container_images_api = ContainerImagesAPI(cls.client)
        cls.get_ansible_cfg_before_test()
        cls.galaxy_api_prefix = os.getenv(
            "PULP_GALAXY_API_PATH_PREFIX", "/api/galaxy").rstrip("/")

    def tearDown(self):
        """Clean class-wide variable."""
        with open("ansible.cfg", "w") as f:
            f.write(self.previous_ansible_cfg)
        delete_orphans()

    @classmethod
    def get_token(cls):
        """Get a Galaxy NG token."""
        return cls.smash_client.post(f"{cls.galaxy_api_prefix}/v3/auth/token/")["token"]

    @classmethod
    def get_ansible_cfg_before_test(cls):
        """Update ansible.cfg to use the given base_path."""
        try:
            with open("ansible.cfg", "r") as f:
                cls.previous_ansible_cfg = f.read()
        except FileNotFoundError:
            cls.previous_ansible_cfg = (
                "[defaults]\n"
                "remote_tmp = /tmp/ansible\n"
                "local_tmp = /tmp/ansible\n"
            )


    def update_ansible_cfg(self, base_path, auth=True):
        """Update ansible.cfg to use the given base_path."""
        token = f"token={self.get_token()}" if auth else ""
        ansible_cfg = (
            f"{self.previous_ansible_cfg}\n"
            "[galaxy]\n"
            "server_list = community_repo\n"
            "\n"
            "[galaxy_server.community_repo]\n"
            f"url={self.cfg.get_base_url()}"
            f"{self.galaxy_api_prefix}/content/{base_path}/\n"
            f"{token}"
        )
        with open("ansible.cfg", "w") as f:
            f.write(ansible_cfg)

    def sync_repo(self, requirements_file, **kwargs):
        """Sync a repository with a given requirements_file"""
        repo_name = kwargs.get("repo_name", "community")
        url = kwargs.get("url", "https://galaxy.ansible.com/api/")

        self.sync_config_api.update(
            repo_name,
            {
                "url": f"{url}",
                "requirements_file": f"{requirements_file}",
            },
        )

        response = self.sync_api.sync(repo_name)
        api_root = os.environ.get("PULP_API_ROOT", "/pulp/")
        monitor_task(f"{api_root}api/v3/tasks/{response.task}/")

    def delete_namespace(self, namespace_name):
        """Delete a Namespace"""
        # namespace_api does not support delete, so we can use the smash_client directly
        self.smash_client.delete(
            f"{self.galaxy_api_prefix}/v3/namespaces/{namespace_name}"
        )

    def delete_collection(self, collection_namespace, collection_name):
        """Delete a Collection"""
        monitor_task(self.collections_api.delete(
            namespace=collection_namespace,
            name=collection_name,
            path="published"
        ).task)
