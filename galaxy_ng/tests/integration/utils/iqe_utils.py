"""Utility functions for AH tests."""
import os
from unittest.mock import patch

from galaxykit import GalaxyClient

import logging
from functools import lru_cache
from pkg_resources import Requirement
from urllib.parse import urljoin

from ansible.galaxy.api import GalaxyAPI
from ansible.galaxy.token import BasicAuthToken
from ansible.galaxy.token import GalaxyToken
from ansible.galaxy.token import KeycloakToken

from galaxy_ng.tests.integration.utils import get_client

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
        self, access_token=None, auth_url=None, validate_certs=False, username=None, password=None
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


@lru_cache()
def get_hub_version(ansible_config):
    if is_standalone():
        role = "iqe_admin"
    elif is_ephemeral_env():
        # TODO: this call should be done by galaxykit
        config = ansible_config("org_admin")
        api_client = get_client(config, request_token=True, require_auth=True)
        return api_client("/", args={}, method="GET")["galaxy_ng_version"]
    else:
        role = "admin"
    gc = GalaxyKitClient(ansible_config).gen_authorized_client(role)
    return gc.get(gc.galaxy_root)["galaxy_ng_version"]


def min_hub_version(ansible_config, spec):
    version = get_hub_version(ansible_config)
    return Requirement.parse(f"galaxy_ng<{spec}").specifier.contains(version)


def max_hub_version(ansible_config, spec):
    version = get_hub_version(ansible_config)
    return Requirement.parse(f"galaxy_ng>{spec}").specifier.contains(version)


client_cache = {}


class GalaxyKitClient:
    def __init__(self, ansible_config):
        self.config = ansible_config

    def gen_authorized_client(
        self,
        role,
        container_engine="podman",
        container_registry=None,
        *,
        ignore_cache=False,
        token=None,
        remote=False
    ):
        config = self.config()
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
                profile_config = self.config("remote_admin") \
                    if remote else self.config("local_admin")
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
                    if remote else profile_config.get("local_auth_url"),
                    "token": token,
                }
            else:
                url = config.get("url")
                if isinstance(role, str):
                    profile_config = self.config(role)
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
                        "auth_url": profile_config.get("auth_url"),
                        "token": token,
                    }
                else:
                    token = get_standalone_token(
                        role, url, ignore_cache=ignore_cache, ssl_verify=ssl_verify
                    )  # ignore_cache=True
                    role.update(token=token)
                    auth = role

            container_engine = config.get("container_engine")
            container_registry = config.get("container_registry")

            g_client = GalaxyClient(
                url,
                auth=auth,
                container_engine=container_engine,
                container_registry=container_registry,
                container_tls_verify=ssl_verify,
                https_verify=ssl_verify,
            )
            if ignore_cache:
                return g_client
            else:
                client_cache[cache_key] = g_client
        return client_cache[cache_key]


token_cache = {}


def get_standalone_token(user, server, *, ignore_cache=False, ssl_verify=True):
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
                token_cache[cache_key] = GalaxyToken(token_value).config["token"]
        else:
            token = BasicAuthToken(username, password)
            if is_ephemeral_env():
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
    return os.getenv('HUB_LOCAL', False)


def is_ephemeral_env():
    return 'ephemeral' in os.getenv('HUB_API_ROOT', 'http://localhost:5001/api/automation-hub/')


def is_stage_environment():
    return os.getenv('TESTS_AGAINST_STAGE', False)


def is_sync_testing():
    return os.getenv('SYNC_TESTS_STAGE', False)


def get_all_collections(api_client, repo):
    """
    This will get a maximum of 100 collections. If the system has more,
    we'll only get 100 so tests using this method might fail as the
    order of the collections is not guaranteed and the expected collection
    might not be returned within the 100 collections.
    """
    url = f'content/{repo}/v3/collections/?limit=100&offset=0'
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
        if local_collection["name"] == artifact.name and \
                local_collection["namespace"] == artifact.namespace:
            local_collection_found = local_collection
    return local_collection_found
