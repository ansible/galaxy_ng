"""Utility functions for AH tests."""
from unittest.mock import patch

from galaxykit import GalaxyClient

try:
    import importlib.resources as pkg_resources
except ModuleNotFoundError:
    import importlib_resources as pkg_resources
import json
import logging
from functools import lru_cache
from pkg_resources import Requirement
from urllib.parse import urljoin


from ansible import context
from ansible.galaxy.api import GalaxyAPI
from ansible.galaxy.token import BasicAuthToken
from ansible.galaxy.token import GalaxyToken
from ansible.galaxy.token import KeycloakToken


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


def get_client(config, request_token=True, headers=None):
    """Get an API client given a role."""
    headers = headers or {}
    server = config["url"]
    auth_url = config.get("auth_url")
    grant_type = config.get("grant_type")
    username = None
    password = None
    if grant_type == "password":
        username = config.get("username")
        password = config.get("password")

    context.CLIARGS = {
        "ignore_certs": config["ssl_verify"],
    }

    token = config.get("token") or None
    if request_token:
        if token:
            if auth_url:
                token = KeycloakToken(config["token"], auth_url=auth_url)
            else:
                token = GalaxyToken(config["token"])
        else:
            if auth_url and grant_type == "password":
                token = KeycloakPassword(
                    auth_url=auth_url,
                    username=username,
                    password=password,
                )
            else:
                token = BasicAuthToken(config["username"], config["password"])
    else:
        token = None

    validate_certs = config["ssl_verify"]
    client = GalaxyAPI(
        None, "automation_hub", url=server, token=token, validate_certs=validate_certs
    )

    def request(url, *args, **kwargs):
        url = urljoin(server, url)

        if isinstance(kwargs.get("args"), dict):
            kwargs["args"] = json.dumps(kwargs["args"])
            headers["Content-Type"] = "application/json"

        if headers:
            if "headers" in kwargs:
                kwargs["headers"].update(headers)
            else:
                kwargs["headers"] = headers
        logger.debug(f"Calling galaxy url: \n{url}")
        logger.debug(f"args: \n{args}")
        logger.debug(f"kwargs: \n{kwargs}")
        result = client._call_galaxy(url, *args, **kwargs)
        logger.debug(f"result: \n{result}")
        return result

    request.config = config
    return request


@lru_cache()
def get_hub_version(ansible_config):
    gc = GalaxyKitClient(ansible_config).gen_authorized_client("admin")
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
