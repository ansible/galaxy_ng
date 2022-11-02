import os
import shutil
import time
from functools import lru_cache
from urllib.parse import urlparse

import pytest
from orionutils.utils import increment_version

from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_ONETIME

from .constants import USERNAME_PUBLISHER
from .utils import (
    ansible_galaxy,
    build_collection,
    get_all_namespaces,
    get_client,
    set_certification,
)
from .utils import upload_artifact as _upload_artifact

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
"""


def pytest_configure(config):
    for line in MARKER_CONFIG.split('\n'):
        if not line:
            continue
        config.addinivalue_line('markers', line)


def is_stage_environment():
    return os.getenv('TESTS_AGAINST_STAGE', False)


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
        "ldap": {  # this is a superuser in ldap profile
            "username": "professor",
            "password": "professor",
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
            "basic_user": {
                "username": {"vault_path": "secrets/qe/stage/users/aa_no_access",
                             "vault_key": "username"},
                "password": {"vault_path": "secrets/qe/stage/users/aa_no_access",
                             "vault_key": "password"},
                "token": None,
            },
            "partner_engineer": {
                "username": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                             "vault_key": "username"},
                "password": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                             "vault_key": "password"},
                "token": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                          "vault_key": "token"},
            },
            "org_admin": {
                "username": {"vault_path": "secrets/qe/stage/users/rbac_org_admin",
                             "vault_key": "username"},
                "password": {"vault_path": "secrets/qe/stage/users/rbac_org_admin",
                             "vault_key": "password"},
                "token": None,
            },
            "admin": {
                "username": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                             "vault_key": "username"},
                "password": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                             "vault_key": "password"},
                "token": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                          "vault_key": "token"},
            }
        }

    def __init__(self, profile, namespace=None):
        self.profile = profile
        if profile not in self.PROFILES.keys():
            raise Exception("AnsibleConfigFixture profile unknown")
        self.namespace = namespace

        # workaround for a weird error with the galaxy cli lib ...
        galaxy_token_fn = os.path.expanduser('~/.ansible/galaxy_token')
        if not os.path.exists(os.path.dirname(galaxy_token_fn)):
            os.makedirs(os.path.dirname(galaxy_token_fn))
        if not os.path.exists(galaxy_token_fn):
            with open(galaxy_token_fn, 'w') as f:
                f.write('')

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
            # tells the tests whether or not to try to mark
            # an imported collection as "published". This happens
            # automatically in the default config for standalone,
            # so should return False in that case ...

            if os.environ.get('HUB_UPLOAD_SIGNATURES'):
                val = os.environ['HUB_UPLOAD_SIGNATURES']
                if str(val) in ['1', 'True', 'true']:
                    return True

            # standalone ...
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

        else:
            raise Exception(f'Unknown config key: {self.namespace}.{key}')

        return super().__getitem__(key)

    def get(self, key):
        return self.__getitem__(key)


@pytest.fixture
def ansible_config():
    return AnsibleConfigFixture


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

    # wait for move task from `inbound-<namespace>` repo to `staging` repo
    time.sleep(SLEEP_SECONDS_ONETIME)

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

    # wait for move task from `inbound-<namespace>` repo to `staging` repo
    time.sleep(SLEEP_SECONDS_ONETIME)

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

    # wait for move task from `inbound-<namespace>` repo to `staging` repo
    time.sleep(SLEEP_SECONDS_ONETIME)

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

    # wait for move task from `inbound-<namespace>` repo to `staging` repo
    time.sleep(SLEEP_SECONDS_ONETIME)

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

    # wait for move task from `inbound-<namespace>` repo to `staging` repo
    time.sleep(SLEEP_SECONDS_ONETIME)

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
