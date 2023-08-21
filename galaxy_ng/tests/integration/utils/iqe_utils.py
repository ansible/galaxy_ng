"""Utility functions for AH tests."""
import os
import subprocess
from unittest.mock import patch

from galaxy_ng.tests.integration.constants import BETA_GALAXY_STAGE_PROFILES

from galaxykit import GalaxyClient

import logging
from urllib.parse import urljoin

from ansible.galaxy.api import GalaxyAPI
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
    return "ephemeral" in os.getenv(
        "HUB_API_ROOT", "http://localhost:5001/api/automation-hub/"
    )


def is_beta_galaxy_stage():
    return "beta-galaxy-stage.ansible" in os.getenv(
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
    return api_client(url)


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


def beta_galaxy_user_cleanup(gc, u):
    gc_admin = gc("admin")
    github_user_username = BETA_GALAXY_STAGE_PROFILES[u]["username"]
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
