import logging
import os
import shutil
from functools import lru_cache
from urllib.parse import urlparse

import pytest
from orionutils.utils import increment_version
from pkg_resources import parse_version

from .constants import USERNAME_PUBLISHER
from .utils import (
    ansible_galaxy,
    build_collection,
    get_all_namespaces,
    get_client,
    set_certification,
    set_synclist,
    iterate_all
)
from .utils import upload_artifact as _upload_artifact
from .utils.iqe_utils import GalaxyKitClient, get_hub_version, is_stage_environment, is_sync_testing

# from orionutils.generator import build_collection


MARKER_CONFIG = """
qa: Mark tests to run in the vortex job.
galaxyapi_smoke: Smoke tests for galaxy-api backend.
standalone_only: Tests that should not run against the Insights version of Hub.
cloud_only: Tests that should not run against the standalone version of Hub.
community_only: Tests relevant to the community deployment profile.
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
"""


logger = logging.getLogger(__name__)


def pytest_configure(config):
    for line in MARKER_CONFIG.split('\n'):
        if not line:
            continue
        config.addinivalue_line('markers', line)


class AnsibleConfigFixture(dict):
    # The class is instantiated with a "profile" that sets
    # which type of user will be used in the test
    PROFILES = {
        "anonymous_user": {
            "username": None,
            "password": None,
            "token": None,
        },
        "basic_user": {
            "username": "iqe_normal_user",
            "password": "redhat",
            "token": "abcdefghijklmnopqrstuvwxyz1234567891",
        },
        "partner_engineer": {
            "username": "jdoe",
            "password": "redhat",
            "token": "abcdefghijklmnopqrstuvwxyz1234567892",
        },
        "org_admin": {  # user is org admin in keycloak
            "username": "org-admin",
            "password": "redhat",
            "token": "abcdefghijklmnopqrstuvwxyz1234567893",
        },
        "admin": {  # this is a superuser
            "username": "notifications_admin",
            "password": "redhat",
            "token": "abcdefghijklmnopqrstuvwxyz1234567894",
        },
        "iqe_admin": {  # this is a superuser
            "username": "iqe_admin",
            "password": "redhat",
            "token": None,
        },
        "ldap": {  # this is a superuser in ldap profile
            "username": "professor",
            "password": "professor",
            "token": None,
        },
        "ldap_non_admin": {  # this is a regular user in ldap profile
            "username": "fry",
            "password": "fry",
            "token": None,
        },
        "ee_admin": {
            "username": "ee_admin",
            "password": "redhat",
            "token": "abcdefghijklmnopqrstuvwxyz1234567895",
        },
        "github_user_1": {
            "username": "gh01",
            "password": "redhat",
            "token": None,
        },
        "github_user_2": {
            "username": "gh02",
            "password": "redhat",
            "token": None,
        },
        "geerlingguy": {
            "username": "geerlingguy",
            "password": "redhat",
            "token": None,
        },
        "jctannerTEST": {
            "username": "jctannerTEST",
            "password": "redhat",
            "token": None,
        },
    }
    if is_stage_environment():
        PROFILES = {
            # ns owner to autohubtest2, not in partner engineer group, not an SSO org admin
            "basic_user": {
                "username": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-basic",
                             "vault_key": "username"},
                "password": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-basic",
                             "vault_key": "password"},
                "token": None,
            },
            # in partner engineer group, not an SSO org admin username: ansible-hub-qe-pe2
            "partner_engineer": {
                "username": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                             "vault_key": "username"},
                "password": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                             "vault_key": "password"},
                "token": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                          "vault_key": "token"},
            },
            # an SSO org admin, not in partner engineer group
            "org_admin": {
                "username": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-rbac",
                             "vault_key": "username"},
                "password": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-rbac",
                             "vault_key": "password"},
                "token": None,
            },
            # for stage env, this can be same user as partner_engineer profile
            "admin": {
                "username": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                             "vault_key": "username"},
                "password": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                             "vault_key": "password"},
                "token": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                          "vault_key": "token"},
            }
        }

    def __init__(self, profile=None, namespace=None, url=None, auth_url=None):
        self.url = url
        self.auth_url = auth_url
        self.profile = profile
        self.namespace = namespace

        # workaround for a weird error with the galaxy cli lib ...
        galaxy_token_fn = os.path.expanduser('~/.ansible/galaxy_token')
        if not os.path.exists(os.path.dirname(galaxy_token_fn)):
            os.makedirs(os.path.dirname(galaxy_token_fn))
        if not os.path.exists(galaxy_token_fn):
            with open(galaxy_token_fn, 'w') as f:
                f.write('')

        if self.profile:
            if isinstance(self.PROFILES[self.profile]["username"], dict):
                # credentials from vault
                loader = get_vault_loader()
                self._set_profile_from_vault(loader, self.profile, "username")
                self._set_profile_from_vault(loader, self.profile, "password")
                if self.PROFILES[self.profile]["token"]:
                    self._set_profile_from_vault(loader, self.profile, "token")

    def _set_profile_from_vault(self, loader, profile, param):
        param_vault_path = self.PROFILES[profile][param]["vault_path"]
        param_vault_key = self.PROFILES[profile][param]["vault_key"]
        param_from_vault = loader.get_value_from_vault(path=param_vault_path, key=param_vault_key)
        self.PROFILES[profile][param] = param_from_vault

    def __repr__(self):
        return f'<AnsibleConfigFixture: {self.namespace}>'

    def __getitem__(self, key):

        if key == 'url':
            # The "url" key is actually the full url to the api root.
            if self.url:
                return self.url
            else:
                return os.environ.get(
                    'HUB_API_ROOT',
                    'http://localhost:5001/api/automation-hub/'
                )
        elif key == 'api_prefix':
            # strip the proto+host+port from the api root
            api_root = os.environ.get(
                'HUB_API_ROOT',
                'http://localhost:5001/api/automation-hub/'
            )
            parsed = urlparse(api_root)
            return parsed.path

        elif key == 'auth_url':
            # The auth_url value should be None for a standalone stack.
            if self.auth_url:
                return self.auth_url
            else:
                return os.environ.get(
                    'HUB_AUTH_URL',
                    None
                )

        elif key == "token":
            return self.PROFILES[self.profile]["token"]

        elif key == "username":
            return self.PROFILES[self.profile]["username"]

        elif key == "password":
            return self.PROFILES[self.profile]["password"]

        elif key == 'use_move_endpoint':
            # tells the tests whether or not to try to mark
            # an imported collection as "published". This happens
            # automatically in the default config for standalone,
            # so should return False in that case ...

            if os.environ.get('HUB_USE_MOVE_ENDPOINT'):
                val = os.environ['HUB_USE_MOVE_ENDPOINT']
                if str(val) in ['1', 'True', 'true']:
                    return True

            # standalone ...
            return False

            # cloud ...
            # return True

        elif key == 'upload_signatures':
            if os.environ.get('HUB_UPLOAD_SIGNATURES'):
                val = os.environ['HUB_UPLOAD_SIGNATURES']
                if str(val) in ['1', 'True', 'true']:
                    return True
            return False

        elif key == 'github_url':
            return os.environ.get(
                'SOCIAL_AUTH_GITHUB_BASE_URL',
                'http://localhost:8082'
            )

        elif key == 'github_api_url':
            return os.environ.get(
                'SOCIAL_AUTH_GITHUB_API_URL',
                'http://localhost:8082'
            )

        elif key == 'ssl_verify':
            return os.environ.get(
                'SSL_VERIFY',
                False
            )

        elif key == 'container_engine':
            return os.environ.get(
                'CONTAINER_ENGINE',
                'podman'
            )

        elif key == 'container_registry':
            return os.environ.get(
                'CONTAINER_REGISTRY',
                'localhost:5001'
            )

        elif key == 'server':
            return self["url"].split("/api/")[0]

        else:
            raise Exception(f'Unknown config key: {self.namespace}.{key}')

        return super().__getitem__(key)

    def get(self, key):
        return self.__getitem__(key)

    def get_profile_data(self):
        if self.profile:
            return self.PROFILES[self.profile]
        raise Exception("No profile has been set")


@pytest.fixture(scope="session")
def ansible_config():
    return get_ansible_config()


def get_ansible_config():
    if is_sync_testing():
        return AnsibleConfigSync
    else:
        return AnsibleConfigFixture


def get_ansible_config_sync():
    return AnsibleConfigSync


@pytest.fixture(scope="function")
def published(ansible_config, artifact):

    # make sure the expected namespace exists ...
    config = ansible_config("partner_engineer")
    api_prefix = config.get("api_prefix")
    api_prefix = api_prefix.rstrip("/")
    api_client = get_client(config)
    existing = dict((x['name'], x) for x in get_all_namespaces(api_client=api_client))
    if artifact.namespace not in existing:
        payload = {'name': artifact.namespace, 'groups': []}
        api_client(f'{api_prefix}/v3/namespaces/', args=payload, method='POST')

    # publish
    ansible_galaxy(
        f"collection publish {artifact.filename} -vvv --server=automation_hub",
        ansible_config=ansible_config("partner_engineer", namespace=artifact.namespace)
    )

    # certify
    set_certification(api_client, artifact)

    return artifact


@pytest.fixture(scope="function")
def certifiedv2(ansible_config, artifact):
    """ Create and publish+certify collection version N and N+1 """

    # make sure the expected namespace exists ...
    config = ansible_config("partner_engineer")
    api_prefix = config.get("api_prefix")
    api_prefix = api_prefix.rstrip("/")
    api_client = get_client(config)
    existing = dict((x['name'], x) for x in get_all_namespaces(api_client=api_client))
    if artifact.namespace not in existing:
        payload = {'name': artifact.namespace, 'groups': []}
        api_client(f'{api_prefix}/v3/namespaces/', args=payload, method='POST')

    # publish v1
    ansible_galaxy(
        f"collection publish {artifact.filename}",
        ansible_config=ansible_config("partner_engineer", namespace=artifact.namespace)
    )

    # certify v1
    set_certification(api_client, artifact)

    # Increase collection version
    new_version = increment_version(artifact.version)
    artifact2 = build_collection(
        key=artifact.key,
        namespace=artifact.namespace,
        name=artifact.name,
        version=new_version
    )

    # publish newer version
    ansible_galaxy(
        f"collection publish {artifact2.filename}",
        ansible_config=ansible_config("partner_engineer", namespace=artifact.namespace)
    )

    # certify newer version
    set_certification(api_client, artifact2)

    return (artifact, artifact2)


@pytest.fixture(scope="function")
def uncertifiedv2(ansible_config, artifact):
    """ Create and publish collection version N and N+1 but only certify N"""

    # make sure the expected namespace exists ...
    config = ansible_config("partner_engineer")
    api_prefix = config.get("api_prefix")
    api_prefix = api_prefix.rstrip("/")
    api_client = get_client(config)
    existing = dict((x['name'], x) for x in get_all_namespaces(api_client=api_client))
    if artifact.namespace not in existing:
        payload = {'name': artifact.namespace, 'groups': []}
        api_client(f'{api_prefix}/v3/namespaces/', args=payload, method='POST')

    # publish
    ansible_galaxy(
        f"collection publish {artifact.filename}",
        ansible_config=ansible_config("basic_user", namespace=artifact.namespace)
    )

    # certify v1
    set_certification(api_client, artifact)

    # Increase collection version
    new_version = increment_version(artifact.version)
    artifact2 = build_collection(
        key=artifact.key,
        namespace=artifact.namespace,
        name=artifact.name,
        version=new_version
    )

    # Publish but do -NOT- certify newer version ...
    ansible_galaxy(
        f"collection publish {artifact2.filename}",
        ansible_config=ansible_config("basic_user", namespace=artifact.namespace)
    )

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


@lru_cache()
def get_vault_loader():
    from .utils.vault_loading import VaultSecretFetcher
    vault_settings = {
        'IQE_VAULT_VERIFY': True,
        'IQE_VAULT_URL': 'https://vault.devshift.net',
        'IQE_VAULT_GITHUB_TOKEN': os.environ.get('IQE_VAULT_GITHUB_TOKEN'),
        'IQE_VAULT_ROLE_ID': os.environ.get('IQE_VAULT_ROLE_ID'),
        'IQE_VAULT_SECRET_ID': os.environ.get('IQE_VAULT_SECRET_ID'),
        'IQE_VAULT_LOADER_ENABLED': True,
        'IQE_VAULT_MOUNT_POINT': 'insights'
    }
    return VaultSecretFetcher.from_settings(vault_settings)


@pytest.fixture(scope="session")
def galaxy_client(ansible_config):
    return get_galaxy_client(ansible_config)


class AnsibleConfigSync(AnsibleConfigFixture):
    PROFILES = {
        "remote_admin": {
            "username": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                         "vault_key": "username"},
            "password": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                         "vault_key": "password"},
            "token": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                      "vault_key": "token"},
        },
        "local_admin": {  # this is a superuser
            "username": "admin",
            "password": "admin",
            "token": None,
        }
    }

    def __init__(self, profile=None, namespace=None):
        super().__init__(profile, namespace)

    def __getitem__(self, key):
        if key == 'remote_hub':
            # The "url" key is actually the full url to the api root.
            return os.environ.get(
                'REMOTE_HUB',
                'https://console.stage.redhat.com/api/automation-hub/'
            )
        if key == 'remote_auth_url':
            # The "url" key is actually the full url to the api root.
            return os.environ.get(
                'REMOTE_AUTH_URL',
                'https://sso.stage.redhat.com/auth/realms/'
                'redhat-external/protocol/openid-connect/token/'
            )
        if key == 'local_hub':
            # The "url" key is actually the full url to the api root.
            return os.environ.get(
                'LOCAL_HUB',
                'http://localhost:5001/api/automation-hub/'
            )
        if key == 'local_auth_url':
            # The "url" key is actually the full url to the api root.
            return os.environ.get(
                'LOCAL_AUTH_URL',
                None
            )
        return super().__getitem__(key)


def get_galaxy_client(ansible_config):
    """
    Returns a function that, when called with one of the users listed in the settings.local.yaml
    file will login using hub and galaxykit, returning the constructed GalaxyClient object.
    """
    galaxy_kit_client = GalaxyKitClient(ansible_config)
    return galaxy_kit_client.gen_authorized_client


def pytest_sessionstart(session):
    hub_version = get_hub_version(get_ansible_config())
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

    url = os.getenv("TEST_CRC_API_ROOT", "http://localhost:8080/api/automation-hub/")
    auth_url = os.getenv(
        "TEST_CRC_AUTH_URL",
        "http://localhost:8080/auth/realms/redhat-external/protocol/openid-connect/token"
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
    api_client = get_client(ansible_config("admin"))
    return api_client("_ui/v1/settings/")
