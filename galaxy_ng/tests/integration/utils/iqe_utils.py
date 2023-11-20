"""Utility functions for AH tests."""
import os
import subprocess
from functools import lru_cache
from unittest.mock import patch

from pkg_resources import parse_version

from galaxy_ng.tests.integration.constants import GALAXY_STAGE_ANSIBLE_PROFILES, \
    EPHEMERAL_PROFILES, PROFILES, CREDENTIALS, SYNC_PROFILES, DEPLOYED_PAH_PROFILES
from galaxy_ng.tests.integration.utils import get_client

from galaxykit import GalaxyClient

import logging
from urllib.parse import urljoin, urlparse

from ansible.galaxy.api import GalaxyAPI, GalaxyError
from ansible.galaxy.token import BasicAuthToken
from ansible.galaxy.token import GalaxyToken
from ansible.galaxy.token import KeycloakToken

from galaxykit.groups import delete_group
from galaxykit.namespaces import delete_namespace, delete_v1_namespace
from galaxykit.users import delete_user
from galaxykit.utils import GalaxyClientError

logger = logging.getLogger(__name__)


# FILENAME_INCLUDED
# FILENAME_EXCLUDED
# FILENAME_MISSING


class KeycloakPassword(KeycloakToken):
    """
    Class to request an access token to Keycloak server providing username and password.
    Used when environment is ephemeral-cloud.
    """

    def __init__(
        self,
        access_token=None,
        auth_url=None,
        validate_certs=False,
        username=None,
        password=None,
    ):
        self.username = username
        self.password = password
        super().__init__(
            access_token=access_token, auth_url=auth_url, validate_certs=validate_certs
        )

    def _form_payload(self):
        return (
            f"grant_type=password&client_id=cloud-services&"
            f"username={self.username}&password={self.password}"
        )


class TaskWaitingTimeout(Exception):
    pass


class CapturingGalaxyError(Exception):
    def __init__(self, http_error, message):
        self.http_error = http_error
        self.message = message


class CompletedProcessError(Exception):
    pass


client_cache = {}


def remove_from_cache(role):
    for e in list(client_cache.keys()):
        if role in e:
            client_cache.pop(e)
            logger.debug(f"key {e} removed from GalaxyKitClient cache")


class GalaxyKitClient:
    def __init__(self, ansible_config, custom_config=None, basic_token=None):
        self.config = ansible_config if not custom_config else custom_config
        self._basic_token = basic_token

    def gen_authorized_client(
        self,
        role=None,
        container_engine="podman",
        container_registry=None,
        *,
        ignore_cache=False,
        token=None,
        remote=False,
        basic_token=False,
        github_social_auth=False
    ):

        self._basic_token = basic_token
        try:
            config = self.config()
        except TypeError:
            config = self.config
        if not role:
            return GalaxyClient(galaxy_root=config.get("url"), auth=None)
        # role can be either be the name of a user (like `ansible_insights`)
        # or a dict containing a username and password:
        # {"username": "autohubtest2", "password": "p@ssword!"}
        if isinstance(role, dict):
            cache_key = (role["username"], container_engine, container_registry, token)
        else:
            cache_key = (role, container_engine, container_registry, token)
        ssl_verify = config.get("ssl_verify")
        if cache_key not in client_cache or ignore_cache:
            if is_sync_testing():
                url = config.get("remote_hub") if remote else config.get("local_hub")
                profile_config = (
                    self.config("remote_admin") if remote else self.config("local_admin")
                )
                user = profile_config.get_profile_data()
                if profile_config.get("auth_url"):
                    token = profile_config.get("token")
                if token is None:
                    token = get_standalone_token(
                        user, url, ssl_verify=ssl_verify, ignore_cache=ignore_cache
                    )

                auth = {
                    "username": user["username"],
                    "password": user["password"],
                    "auth_url": profile_config.get("remote_auth_url")
                    if remote
                    else profile_config.get("local_auth_url"),
                    "token": token,
                }
            else:
                url = config.get("url")
                if isinstance(role, str):
                    profile_config = self.config(role)
                    user = profile_config
                    if not github_social_auth:
                        if profile_config.get("auth_url"):
                            token = profile_config.get("token")
                        if token is None:
                            token = get_standalone_token(
                                user, url, ssl_verify=ssl_verify, ignore_cache=ignore_cache,
                                basic_token=self._basic_token
                            )
                    auth = {
                        "username": user["username"],
                        "password": user["password"],
                        "auth_url": profile_config.get("auth_url"),
                        "token": token,
                    }
                elif not github_social_auth:
                    token = get_standalone_token(
                        role,
                        url,
                        ignore_cache=ignore_cache,
                        ssl_verify=ssl_verify,
                        basic_token=basic_token,
                    )  # ignore_cache=True
                    role.update(token=token)
                    auth = role
                else:
                    auth = role
            container_engine = config.get("container_engine")
            container_registry = config.get("container_registry")
            token_type = None if not basic_token else "Basic"
            g_client = GalaxyClient(
                url,
                auth=auth,
                container_engine=container_engine,
                container_registry=container_registry,
                container_tls_verify=ssl_verify,
                https_verify=ssl_verify,
                token_type=token_type,
                github_social_auth=github_social_auth
            )
            client_cache[cache_key] = g_client
            if ignore_cache:
                return g_client
        return client_cache[cache_key]


token_cache = {}


def get_standalone_token(
    user, server, *, ignore_cache=False, ssl_verify=True, basic_token=False
):
    cache_key = f"{server}::{user['username']}"

    if cache_key not in token_cache or ignore_cache:
        username = user["username"]
        password = user.get("password")
        token_value = user.get("token")
        auth_url = user.get("auth_url")

        if token_value:
            if auth_url:
                token = KeycloakToken(token_value, auth_url=auth_url)
                token_cache[cache_key] = token.get()
            else:
                token = GalaxyToken(token_value)
                token_cache[cache_key] = token.config["token"]
        else:
            token = BasicAuthToken(username, password)
            if basic_token:
                token_cache[cache_key] = token.get()
            else:
                with patch("ansible.context.CLIARGS", {"ignore_certs": True}):
                    anon_client = GalaxyAPI(
                        None,
                        "automation_hub",
                        url=server,
                        token=token,
                        validate_certs=ssl_verify,
                    )
                url = urljoin(server, "v3/auth/token/")
                resp = anon_client._call_galaxy(url, method="POST", auth_required=True)
                token_cache[cache_key] = resp["token"]

    return token_cache[cache_key]


def is_standalone():
    local = os.getenv("HUB_LOCAL", False)
    if local:
        return local not in ("0", "false")
    return local


def is_ephemeral_env():
    return "c-rh-c-eph" in os.getenv(
        "HUB_API_ROOT", "http://localhost:5001/api/automation-hub/"
    )


def is_galaxy_stage():
    return "galaxy-stage.ansible" in os.getenv(
        "HUB_API_ROOT", "http://localhost:5001/api/automation-hub/"
    )


def is_ocp_env():
    # this check will not be necessary when content signing is enabled in operator
    # we also have containerized aap, in that case check proper env var as well
    return ("ocp4.testing.ansible.com" in os.getenv(
        "HUB_API_ROOT", "http://localhost:5001/api/automation-hub/")
        or os.getenv("HUB_CONTENT_SIGNING_ENABLED", 'true') not in ['1', 'True', 'true'])


def is_stage_environment():
    return os.getenv("TESTS_AGAINST_STAGE", False)


def is_sync_testing():
    return os.getenv("SYNC_TESTS_STAGE", False)


def is_dev_env_standalone():
    dev_env_standalone = os.getenv("DEV_ENV_STANDALONE", True)
    return dev_env_standalone in ('true', 'True', 1, '1', True)


def avoid_docker_limit_rate():
    avoid_limit_rate = os.getenv("AVOID_DOCKER_LIMIT_RATE", False)
    return avoid_limit_rate in ('true', 'True', 1, '1', True)


def is_upgrade_from_aap23_hub46():
    upgrade = os.getenv("UPGRADE_FROM_AAP23_HUB46", False)
    return upgrade in ('true', 'True', 1, '1', True)


def pull_and_tag_test_image(container_engine, registry, tag=None):
    image = "alpine"
    tag = "alpine:latest" if tag is None else tag
    if avoid_docker_limit_rate():
        image = "quay.io/libpod/alpine"
    subprocess.check_call([container_engine, "pull", image])
    subprocess.check_call(
        [container_engine, "tag", image,
         f"{registry}/{tag}"])
    return image


def get_all_collections(api_client, repo):
    """
    This will get a maximum of 100 collections. If the system has more,
    we'll only get 100 so tests using this method might fail as the
    order of the collections is not guaranteed and the expected collection
    might not be returned within the 100 collections.
    """
    url = f"content/{repo}/v3/collections/?limit=100&offset=0"
    return api_client.get(url)


def retrieve_collection(artifact, collections):
    """looks for a given artifact in the collections list and returns
     the element if found or None otherwise

    Args:
        artifact: The artifact to be found.
        collections: List of collections to iterate over.

    Returns:
        If the artifact is present in the list, it returns the artifact.
        It returns None if the artifact is not found in the list.
    """
    local_collection_found = None
    for local_collection in collections["data"]:
        if (
            local_collection["name"] == artifact.name
            and local_collection["namespace"] == artifact.namespace
        ):
            local_collection_found = local_collection
    return local_collection_found


def galaxy_stage_ansible_user_cleanup(gc, u):
    gc_admin = gc("admin")
    github_user_username = GALAXY_STAGE_ANSIBLE_PROFILES[u]["username"]
    group = f"namespace:{github_user_username}".replace("-", "_")
    try:
        delete_user(gc_admin, github_user_username)
    except ValueError:
        pass
    try:
        delete_group(gc_admin, group)
    except ValueError:
        pass
    try:
        delete_namespace(gc_admin, github_user_username.replace("-", "_"))
    except GalaxyClientError:
        pass
    try:
        delete_v1_namespace(gc_admin, github_user_username)
    except ValueError:
        pass


def get_ansible_config():
    return AnsibleConfigFixture


def get_galaxy_client(ansible_config):
    """
    Returns a function that, when called with one of the users listed in the settings.local.yaml
    file will login using hub and galaxykit, returning the constructed GalaxyClient object.
    """
    galaxy_kit_client = GalaxyKitClient(ansible_config)
    return galaxy_kit_client.gen_authorized_client


class AnsibleConfigFixture(dict):
    # The class is instantiated with a "profile" that sets
    # which type of user will be used in the test

    PROFILES = {}

    def __init__(self, profile=None, namespace=None, url=None, auth_url=None):
        backend_map = {
            "community": "community",
            "galaxy": "galaxy",
            "keycloak": "ldap",
            "ldap": "ldap"
        }
        self._auth_backend = os.environ.get('HUB_TEST_AUTHENTICATION_BACKEND')
        self.url = url
        self.auth_url = auth_url
        self.profile = profile
        self.namespace = namespace

        if is_sync_testing():
            self.PROFILES = SYNC_PROFILES
        elif is_stage_environment():
            self.PROFILES = EPHEMERAL_PROFILES
        elif not is_dev_env_standalone():
            self.PROFILES = DEPLOYED_PAH_PROFILES
            self._set_credentials_when_not_docker_pah()
        elif is_ephemeral_env():
            self.PROFILES = DEPLOYED_PAH_PROFILES
            self.PROFILES["admin"]["token"] = None
            self.PROFILES["org_admin"]["token"] = None
            self.PROFILES["partner_engineer"]["token"] = None
            self.PROFILES["basic_user"]["token"] = None
        elif is_galaxy_stage():
            self.PROFILES = GALAXY_STAGE_ANSIBLE_PROFILES
        else:
            for profile_name in PROFILES:
                p = PROFILES[profile_name]
                credential_set = backend_map.get(self._auth_backend, "galaxy")
                if p['username'] is None:
                    continue

                if username := p["username"].get(credential_set):
                    self.PROFILES[profile_name] = {
                        "username": username,
                        "token": CREDENTIALS[username].get("token"),
                        "password": CREDENTIALS[username].get("password")
                    }

            if self._auth_backend == "community":
                self.PROFILES["anonymous_user"] = PROFILES.get('anonymous_user')

        # workaround for a weird error with the galaxy cli lib ...
        galaxy_token_fn = os.path.expanduser('~/.ansible/galaxy_token')
        if not os.path.exists(os.path.dirname(galaxy_token_fn)):
            os.makedirs(os.path.dirname(galaxy_token_fn))
        if not os.path.exists(galaxy_token_fn):
            with open(galaxy_token_fn, 'w') as f:
                f.write('')

        if profile:
            self.set_profile(profile)

    def __hash__(self):
        # To avoid TypeError: unhashable type: 'AnsibleConfigFixture'
        return hash((self.url, self.auth_url, self.profile, self.namespace))

    def _set_profile_from_vault(self, loader, profile, param):
        param_vault_path = self.PROFILES[profile][param]["vault_path"]
        param_vault_key = self.PROFILES[profile][param]["vault_key"]
        param_from_vault = loader.get_value_from_vault(path=param_vault_path,
                                                       key=param_vault_key)
        self.PROFILES[profile][param] = param_from_vault

    def _set_credentials_when_not_docker_pah(self):
        # if we get here, we are running tests against PAH
        # but not in a containerized development environment (probably from AAP installation),
        # so we need to get the URL and admin credentials (and create some test data)
        admin_pass = os.getenv("HUB_ADMIN_PASS", "AdminPassword")
        self.PROFILES["admin"]["username"] = "admin"
        self.PROFILES["admin"]["password"] = admin_pass
        self.PROFILES["admin"]["token"] = None
        self.PROFILES["iqe_admin"]["username"] = "admin"
        self.PROFILES["iqe_admin"]["password"] = admin_pass
        self.PROFILES["iqe_admin"]["token"] = None
        self.PROFILES["basic_user"]["token"] = None
        self.PROFILES["basic_user"]["password"] = "Th1sP4ssd"
        self.PROFILES["partner_engineer"]["token"] = None
        self.PROFILES["partner_engineer"]["password"] = "Th1sP4ssd"
        self.PROFILES["ee_admin"]["token"] = None
        self.PROFILES["ee_admin"]["password"] = "Th1sP4ssd"
        self.PROFILES["org_admin"]["token"] = None
        self.PROFILES["org_admin"]["password"] = "Th1sP4ssd"
        token = get_standalone_token(self.PROFILES["admin"], server=self.get("url"),
                                     ssl_verify=False)
        self.PROFILES["admin"]["token"] = token

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

        elif key == 'auth_backend':
            return self._auth_backend

        elif key == "token":
            # Generate tokens for LDAP and keycloak backed users
            if self.profile:
                p = self.PROFILES[self.profile]
                try:
                    if CREDENTIALS[p["username"]].get("gen_token", False):
                        return get_standalone_token(p, self["url"])
                    return p.get("token", None)
                except KeyError:
                    return p.get("token", None)
            else:
                return None

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

        elif key == 'remote_hub':
            # The "url" key is actually the full url to the api root.
            return os.environ.get(
                'REMOTE_HUB',
                'https://console.stage.redhat.com/api/automation-hub/'
            )
        elif key == 'remote_auth_url':
            # The "url" key is actually the full url to the api root.
            return os.environ.get(
                'REMOTE_AUTH_URL',
                'https://sso.stage.redhat.com/auth/realms/'
                'redhat-external/protocol/openid-connect/token/'
            )
        elif key == 'local_hub':
            # The "url" key is actually the full url to the api root.
            return os.environ.get(
                'LOCAL_HUB',
                'http://localhost:5001/api/automation-hub/'
            )
        elif key == 'local_auth_url':
            # The "url" key is actually the full url to the api root.
            return os.environ.get(
                'LOCAL_AUTH_URL',
                None
            )

        else:
            raise Exception(f'Unknown config key: {self.namespace}.{key}')

        return super().__getitem__(key)

    def get(self, key):
        return self.__getitem__(key)

    def get_profile_data(self):
        if self.profile:
            return self.PROFILES[self.profile]
        raise Exception("No profile has been set")

    def set_profile(self, profile):
        self.profile = profile
        if isinstance(self.PROFILES[self.profile]["username"], dict):
            # credentials from vault
            loader = get_vault_loader()
            self._set_profile_from_vault(loader, self.profile, "username")
            self._set_profile_from_vault(loader, self.profile, "password")
            if self.PROFILES[self.profile]["token"]:
                self._set_profile_from_vault(loader, self.profile, "token")


def has_old_credentials():
    # FIXME: Old versions have admin/admin. This needs to be fixed
    ansible_config = get_ansible_config()
    hub_version = get_hub_version(ansible_config)
    return parse_version(hub_version) < parse_version('4.7')


@lru_cache()
def get_hub_version(ansible_config):
    if is_standalone():
        role = "iqe_admin"
    elif is_ephemeral_env():
        # I can't get a token from the ephemeral environment.
        # Changed to Basic token authentication until the issue is resolved
        del os.environ["HUB_AUTH_URL"]
        role = "partner_engineer"
        galaxy_client = get_galaxy_client(ansible_config)
        gc = galaxy_client(role, basic_token=True, ignore_cache=True)
        galaxy_ng_version = gc.get(gc.galaxy_root)["galaxy_ng_version"]
        return galaxy_ng_version
    else:
        role = "admin"
    try:
        gc = GalaxyKitClient(ansible_config).gen_authorized_client(role)
    except GalaxyError:
        # FIXME: versions prior to 4.7 have different credentials. This needs to be fixed.
        gc = GalaxyClient(galaxy_root="http://localhost:5001/api/automation-hub/",
                          auth={"username": "admin", "password": "admin"})
    return gc.get(gc.galaxy_root)["galaxy_ng_version"]


@lru_cache()
def get_vault_loader():
    from .vault_loading import VaultSecretFetcher
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


def require_signature_for_approval():
    ansible_config = get_ansible_config()
    config = ansible_config("admin")
    api_client = get_client(config)
    settings = api_client("_ui/v1/settings/")
    return settings.get("GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL")


def sign_collection_on_demand(client, signing_service, repo, ns, collection_name,
                              collection_version):
    # to be moved to galaxykit
    sign_url = "_ui/v1/collection_signing/"
    sign_payload = {
        "signing_service": signing_service,
        "distro_base_path": repo,
        "namespace": ns,
        "collection": collection_name,
        "version": collection_version,
    }
    client.post(sign_url, sign_payload)


def galaxy_auto_sign_collections():
    ansible_config = get_ansible_config()
    config = ansible_config("admin")
    api_client = get_client(config)
    settings = api_client("_ui/v1/settings/")
    return settings.get("GALAXY_AUTO_SIGN_COLLECTIONS")
