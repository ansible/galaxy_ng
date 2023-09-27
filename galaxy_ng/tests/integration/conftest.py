import logging
import os
import shutil

import pytest
from orionutils.utils import increment_version
from pkg_resources import parse_version, Requirement

from galaxykit.collections import delete_collection
from galaxykit.groups import get_group_id
from galaxykit.namespaces import create_namespace
from galaxykit.utils import GalaxyClientError
from .constants import USERNAME_PUBLISHER, BETA_GALAXY_STAGE_PROFILES
from .utils import (
    ansible_galaxy,
    build_collection,
    get_client,
    set_certification,
    set_synclist,
    iterate_all,
    wait_for_url,
)

from .utils import upload_artifact as _upload_artifact
from .utils.iqe_utils import (
    GalaxyKitClient,
    is_dev_env_standalone,
    is_standalone,
    is_ephemeral_env,
    beta_galaxy_user_cleanup, remove_from_cache,
    get_ansible_config, get_galaxy_client, AnsibleConfigFixture, get_hub_version
)
from .utils.tools import generate_random_artifact_version

# from orionutils.generator import build_collection


MARKER_CONFIG = """
qa: Mark tests to run in the vortex job.
galaxyapi_smoke: Smoke tests for galaxy-api backend.
deployment_standalone: Tests that should not run against the Insights version of Hub.
deployment_cloud: Tests that should not run against the standalone version of Hub.
deployment_community: Tests relevant to the community deployment profile.
cli: Tests that shell out to the real ansible-galaxy cli.
ui: Tests that navigate the UI via selenium.
ui_standalone: UI tests that only work in standalone mode.
smoke: Same as galaxyapi_smoke?
prod_status: For checking prod?
busted: Doesn't work yet.
stage_health: For checking stage?
namespace: Tests that manipulate namespaces.
certification: Related to certification.
collection_move: Related to moving collection versions.
collection_delete: Deletes collections.
collection_version_delete: Deletes collections versions.
collection_signing: Related to collection signing.
delete: Tests for deleting objects.
move: Related to the move api.
synclist: Related to synclist object and synclist repo.
openapi: Checks the openapi schema and routes.
openapi_generate_bindings: Verifies pulp client bindings generator
package: tests for the pip packaging
api_ui: tests for the _ui v1 api
importer: tests related checks in galaxy-importer
pulp_api: tests related to the pulp api endpoints
ldap: tests related to the ldap integration
role: Related to RBAC Roles
rbac_roles: Tests checking Role permissions
group: Related to Groups
slow_in_cloud: tests that take too long to be run against stage
max_hub_version: This marker takes an argument that indicates the maximum hub version
min_hub_version: This marker takes an argument that indicates the minimum hub version
iqe_rbac_test: imported iqe tests checking role permissions
sync: sync tests against stage
certified_sync: sync tests container against container
auto_approve: run tests that require AUTO_APPROVE to be set to true
private_repos: run tests verifying private repositories
rbac_repos: tests verifying rbac roles on custom repositories
x_repo_search: tests verifying cross-repo search endpoint
repositories: tests verifying custom repositories
all: tests that are unmarked and should pass in all deployment modes
beta_galaxy: tests tha run against beta-galaxy-stage.ansible.com
"""

logger = logging.getLogger(__name__)


def pytest_configure(config):
    for line in MARKER_CONFIG.split('\n'):
        if not line:
            continue
        config.addinivalue_line('markers', line)


@pytest.fixture(scope="session")
def ansible_config():
    return get_ansible_config()


@pytest.fixture(scope="function")
def published(ansible_config, artifact, galaxy_client):
    # make sure the expected namespace exists ...
    config = ansible_config("partner_engineer")
    api_client = get_client(config)
    gc = galaxy_client("partner_engineer")
    create_namespace(gc, artifact.namespace, "")

    # publish
    config = ansible_config("partner_engineer")
    ansible_galaxy(
        f"collection publish {artifact.filename} -vvv --server=automation_hub",
        ansible_config=config
    )

    # certify
    hub_4_5 = is_hub_4_5(ansible_config)
    set_certification(api_client, gc, artifact, hub_4_5=hub_4_5)

    return artifact


@pytest.fixture(scope="function")
def certifiedv2(ansible_config, artifact, galaxy_client):
    """ Create and publish+certify collection version N and N+1 """

    # make sure the expected namespace exists ...
    config = ansible_config("partner_engineer")
    api_client = get_client(config)
    gc = galaxy_client("partner_engineer")
    create_namespace(gc, artifact.namespace, "")

    # publish v1
    config = ansible_config("partner_engineer")
    ansible_galaxy(
        f"collection publish {artifact.filename}",
        ansible_config=config
    )

    # certify v1
    hub_4_5 = is_hub_4_5(ansible_config)
    set_certification(api_client, gc, artifact, hub_4_5=hub_4_5)

    # Increase collection version
    new_version = increment_version(artifact.version)
    artifact2 = build_collection(
        key=artifact.key,
        namespace=artifact.namespace,
        name=artifact.name,
        version=new_version
    )

    # publish newer version
    config = ansible_config("partner_engineer")
    ansible_galaxy(
        f"collection publish {artifact2.filename}",
        ansible_config=config
    )

    # certify newer version
    set_certification(api_client, gc, artifact2, hub_4_5=hub_4_5)

    return (artifact, artifact2)


@pytest.fixture(scope="function")
def uncertifiedv2(ansible_config, artifact, settings, galaxy_client):
    """ Create and publish collection version N and N+1 but only certify N"""

    # make sure the expected namespace exists ...
    config = ansible_config("partner_engineer")
    api_client = get_client(config)
    gc = galaxy_client("partner_engineer")
    create_namespace(gc, artifact.namespace, "")

    # publish
    config = ansible_config("basic_user")
    ansible_galaxy(
        f"collection publish {artifact.filename}",
        ansible_config=config
    )

    # certify v1
    hub_4_5 = is_hub_4_5(ansible_config)
    set_certification(api_client, gc, artifact, hub_4_5=hub_4_5)

    # Increase collection version
    new_version = increment_version(artifact.version)
    artifact2 = build_collection(
        key=artifact.key,
        namespace=artifact.namespace,
        name=artifact.name,
        version=new_version
    )

    # Publish but do -NOT- certify newer version ...
    config = ansible_config("basic_user")
    ansible_galaxy(
        f"collection publish {artifact2.filename}",
        ansible_config=config
    )
    dest_url = (
        f"v3/plugin/ansible/content/staging/collections/index/"
        f"{artifact2.namespace}/{artifact2.name}/versions/{artifact2.version}/"
    )
    wait_for_url(api_client, dest_url)
    return artifact, artifact2


@pytest.fixture(scope="function")
def auto_approved_artifacts(ansible_config, artifact, galaxy_client):
    """ Create and publish collection version N and N+1"""

    # make sure the expected namespace exists ...
    config = ansible_config("partner_engineer")
    api_client = get_client(config)
    gc = galaxy_client("partner_engineer")
    create_namespace(gc, artifact.namespace, "")

    # publish
    config = ansible_config("basic_user")
    ansible_galaxy(
        f"collection publish {artifact.filename}",
        ansible_config=config
    )

    dest_url = (
        f"v3/plugin/ansible/content/published/collections/index/"
        f"{artifact.namespace}/{artifact.name}/versions/{artifact.version}/"
    )
    wait_for_url(api_client, dest_url)

    # Increase collection version
    new_version = increment_version(artifact.version)
    artifact2 = build_collection(
        key=artifact.key,
        namespace=artifact.namespace,
        name=artifact.name,
        version=new_version
    )

    # Publish but do -NOT- certify newer version ...
    config = ansible_config("basic_user")
    ansible_galaxy(
        f"collection publish {artifact2.filename}",
        ansible_config=config
    )
    dest_url = (
        f"v3/plugin/ansible/content/published/collections/index/"
        f"{artifact2.namespace}/{artifact2.name}/versions/{artifact2.version}/"
    )
    wait_for_url(api_client, dest_url)
    return artifact, artifact2


@pytest.fixture(scope="function")
def artifact():
    """Generate a randomized collection for testing."""

    artifact = build_collection(
        "skeleton",
        config={
            "namespace": USERNAME_PUBLISHER,
            "tags": ["tools", "database"],
        },
    )
    return artifact


@pytest.fixture
def upload_artifact():
    return _upload_artifact


@pytest.fixture
def cleanup_collections(request):
    """Clean created resources during test executions."""

    def cleanup():
        path = os.path.expanduser(
            f"~/.ansible/collections/ansible_collections/{USERNAME_PUBLISHER}/"
        )
        if os.path.exists(path):
            shutil.rmtree(path)

    request.addfinalizer(cleanup)


@pytest.fixture(scope="session")
def galaxy_client(ansible_config):
    return get_galaxy_client(ansible_config)


def pytest_sessionstart(session):
    ansible_config = get_ansible_config()
    hub_version = get_hub_version(ansible_config)
    if not is_standalone() and not is_ephemeral_env() and not is_dev_env_standalone():
        set_test_data(ansible_config, hub_version)
    logger.debug(f"Running tests against hub version {hub_version}")


def pytest_runtest_setup(item):
    test_min_versions = [mark.args[0] for mark in item.iter_markers(name="min_hub_version")]
    test_max_versions = [mark.args[0] for mark in item.iter_markers(name="max_hub_version")]

    hub_version = get_hub_version(get_ansible_config())

    for min_version in test_min_versions:
        if parse_version(hub_version) < parse_version(min_version):
            pytest.skip(
                f"Minimum hub version to run tests is {min_version} "
                f"but hub version {hub_version} was found"
            )
    for max_version in test_max_versions:
        if parse_version(hub_version) > parse_version(max_version):
            pytest.skip(
                f"Maximum hub version to run tests is {max_version} "
                f"but hub version {hub_version} was found"
            )


@pytest.fixture
def sync_instance_crc():
    """
    Returns a configuration for connecting to an instance of galaxy ng running in
    insights mode to perform syncs from.

    The URL and auth URL for the instance can be set with the TEST_CRC_API_ROOT
    and TEST_CRC_AUTH_URL environment variables.

    The environment that these URLs point to must:
    - contain the test fixture credentials from AnsibleConfigFixture
    - contain at least two collections
    - contain at least one deprecated collection
    - contain at least one signed collection

    A target for this can be loaded using the database dump found in
    dev/data/insights-fixture.tar.gz
    """

    url = os.getenv("TEST_CRC_API_ROOT", "http://localhost:38080/api/automation-hub/")
    auth_url = os.getenv(
        "TEST_CRC_AUTH_URL",
        "http://localhost:38080/auth/realms/redhat-external/protocol/openid-connect/token"
    )

    config = AnsibleConfigFixture(url=url, auth_url=auth_url, profile="org_admin")
    manifest = []

    client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    for cv in iterate_all(client, "_ui/v1/collection-versions/?repository=published"):
        ns = cv["namespace"]
        name = cv["name"]

        is_deprecated = client(f"v3/collections/{ns}/{name}")["deprecated"]

        manifest.append({
            "namespace": ns,
            "name": name,
            "version": cv["version"],
            "is_deprecated": is_deprecated,
            "is_signed": cv["sign_state"] == "signed",
            "content_count": len(cv["contents"]),
            "signatures": cv["metadata"]["signatures"]
        })

    signed_count = 0
    deprecated_count = 0

    for cv in manifest:
        if cv["is_signed"]:
            signed_count += 1
        if cv["is_deprecated"]:
            deprecated_count += 1

    # ensure that the target as at least one signed and deprecated collection
    assert signed_count >= 1
    assert deprecated_count >= 1

    # reset the user's synclist
    set_synclist(client, [])

    return (manifest, config)


@pytest.fixture(scope="function")
def settings(ansible_config):
    config = ansible_config("admin")
    api_client = get_client(config)
    return api_client("_ui/v1/settings/")


def set_test_data(ansible_config, hub_version):
    role = "admin"
    gc = GalaxyKitClient(ansible_config).gen_authorized_client(role)
    gc.create_group("ns_group_for_tests")
    gc.create_group("system:partner-engineers")
    gc.create_group("ee_group_for_tests")
    pe_roles = [
        "galaxy.group_admin",
        "galaxy.user_admin",
        "galaxy.collection_admin",
    ]
    gc.get_or_create_user(username="iqe_normal_user", password="Th1sP4ssd", group=None)
    gc.get_or_create_user(username="org-admin", password="Th1sP4ssd", group=None)
    gc.get_or_create_user(username="jdoe", password="Th1sP4ssd", group=None)
    gc.get_or_create_user(username="ee_admin", password="Th1sP4ssd", group=None)
    ns_group_id = get_group_id(gc, group_name="ns_group_for_tests")
    gc.add_user_to_group(username="iqe_normal_user", group_id=ns_group_id)
    gc.add_user_to_group(username="org-admin", group_id=ns_group_id)
    gc.add_user_to_group(username="jdoe", group_id=ns_group_id)
    pe_group_id = get_group_id(gc, group_name="system:partner-engineers")
    if parse_version(hub_version) < parse_version('4.6'):
        pe_permissions = ["galaxy.view_group",
                          "galaxy.delete_group",
                          "galaxy.add_group",
                          "galaxy.change_group",
                          "galaxy.view_user",
                          "galaxy.delete_user",
                          "galaxy.add_user",
                          "galaxy.change_user",
                          "ansible.delete_collection",
                          "galaxy.delete_namespace",
                          "galaxy.add_namespace",
                          "ansible.modify_ansible_repo_content",
                          "ansible.view_ansiblerepository",
                          "ansible.add_ansiblerepository",
                          "ansible.change_ansiblerepository",
                          "ansible.delete_ansiblerepository",
                          "galaxy.change_namespace",
                          "galaxy.upload_to_namespace",
                          ]
        gc.set_permissions("system:partner-engineers", pe_permissions)
    else:
        for rbac_role in pe_roles:
            try:
                gc.add_role_to_group(rbac_role, pe_group_id)
            except GalaxyClientError:
                # role already assigned to group. It's ok.
                pass

    gc.add_user_to_group(username="jdoe", group_id=pe_group_id)
    gc.create_namespace(name="autohubtest2", group="ns_group_for_tests",
                        object_roles=["galaxy.collection_namespace_owner"])
    gc.create_namespace(name="autohubtest3", group="ns_group_for_tests",
                        object_roles=["galaxy.collection_namespace_owner"])

    ee_group_id = get_group_id(gc, group_name="ee_group_for_tests")
    ee_role = 'galaxy.execution_environment_admin'
    if parse_version(hub_version) < parse_version('4.6'):
        ee_permissions = ["container.delete_containerrepository",
                          "galaxy.add_containerregistryremote",
                          "galaxy.change_containerregistryremote",
                          "galaxy.delete_containerregistryremote"]
        gc.set_permissions("ee_group_for_tests", ee_permissions)
    else:
        try:
            gc.add_role_to_group(ee_role, ee_group_id)
        except GalaxyClientError:
            # role already assigned to group. It's ok.
            pass
    gc.add_user_to_group(username="ee_admin", group_id=ee_group_id)


@pytest.fixture(scope="session")
def hub_version(ansible_config):
    return get_hub_version(ansible_config)


@pytest.fixture(scope="function")
def gh_user_1_post(ansible_config):
    """
    Returns a galaxy kit client with a GitHub user logged into beta galaxy stage
    The user and everything related to it will be removed from beta galaxy stage
    after the test
    """
    gc = get_galaxy_client(ansible_config)
    yield gc("github_user", github_social_auth=True)
    beta_galaxy_user_cleanup(gc, "github_user")
    remove_from_cache("github_user")


@pytest.fixture(scope="function")
def gh_user_1(ansible_config):
    """
    Returns a galaxy kit client with a GitHub user logged into beta galaxy stage
    """
    gc = get_galaxy_client(ansible_config)
    return gc("github_user", github_social_auth=True)


@pytest.fixture(scope="function")
def gh_user_2(ansible_config):
    """
    Returns a galaxy kit client with a GitHub user logged into beta galaxy stage
    """
    gc = get_galaxy_client(ansible_config)
    return gc("github_user_alt", github_social_auth=True)


@pytest.fixture(scope="function")
def gh_user_1_pre(ansible_config):
    """
    Removes everything related to the GitHub user and the user itself and
    returns a galaxy kit client with the same GitHub user logged into beta galaxy stage
    """
    gc = get_galaxy_client(ansible_config)
    beta_galaxy_user_cleanup(gc, "github_user")
    return gc("github_user", github_social_auth=True, ignore_cache=True)


@pytest.fixture(scope="function")
def generate_test_artifact(ansible_config):
    """
    Generates a test artifact and deletes it after the test
    """
    github_user_username = BETA_GALAXY_STAGE_PROFILES["github_user"]["username"]
    expected_ns = f"{github_user_username}".replace("-", "_")
    test_version = generate_random_artifact_version()
    artifact = build_collection(
        "skeleton",
        config={"namespace": expected_ns, "version": test_version, "tags": ["tools"]},
    )
    yield artifact
    galaxy_client = get_galaxy_client(ansible_config)
    gc_admin = galaxy_client("admin")
    delete_collection(gc_admin, namespace=artifact.namespace, collection=artifact.name)


def min_hub_version(ansible_config, spec):
    version = get_hub_version(ansible_config)
    return Requirement.parse(f"galaxy_ng<{spec}").specifier.contains(version)


def max_hub_version(ansible_config, spec):
    version = get_hub_version(ansible_config)
    return Requirement.parse(f"galaxy_ng>{spec}").specifier.contains(version)


def is_hub_4_5(ansible_config):
    hub_version = get_hub_version(ansible_config)
    return parse_version(hub_version) < parse_version('4.6')


# add the "all" label to any unmarked tests
def pytest_collection_modifyitems(items, config):
    for item in items:
        if not any(item.iter_markers()):
            item.add_marker("all")
