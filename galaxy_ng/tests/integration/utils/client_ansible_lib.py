"""Utility functions for AH tests."""

import json
import logging
import os

from ansible import context
from ansible.galaxy.api import GalaxyAPI
from ansible.galaxy.token import BasicAuthToken, GalaxyToken, KeycloakToken

from .urls import url_safe_join


logger = logging.getLogger(__name__)


def get_client(config, require_auth=True, request_token=True, headers=None):
    """Get an API client given a role."""
    headers = headers or {}
    server = config["url"]
    assert "200" not in server
    auth_url = config.get("auth_url")

    # force the galaxy client lib to think the ignore certs kwarg was used
    # NOTE: this does not work with 2.12+
    context.CLIARGS = {"ignore_certs": True}

    # request token implies that upstream test wants to use authentication.
    # however, some tests need to auth but send request_token=False, so this
    # kwarg is poorly named and confusing.
    token = config.get("token") or None

    # Only use token when in standalone mode
    if os.getenv("HUB_LOCAL") is None:
        token = None  # TODO: refactor

    if request_token:
        if token:
            # keycloak must have a unique auth url ...
            if auth_url:
                token = KeycloakToken(config["token"], auth_url=auth_url)
            else:
                token = GalaxyToken(config["token"])
        else:
            token = BasicAuthToken(config["username"], config["password"])
    else:
        if require_auth:
            token = BasicAuthToken(config["username"], config["password"])
        else:
            token = None
    client = GalaxyAPI(None, "automation_hub", url=server, token=token)

    # Fix for 2.12+
    client.validate_certs = False

    # make an api call with the upstream galaxy client lib from ansible core
    def request(url, *args, **kwargs):
        url = url_safe_join(server, url)
        req_headers = dict(headers)
        kwargs_headers = kwargs.get('headers') or {}
        kwargs_headers_keys = list(kwargs_headers.keys())
        kwargs_headers_keys = [x.lower() for x in list(kwargs_headers.keys())]

        if isinstance(kwargs.get("args"), dict):
            kwargs["args"] = json.dumps(kwargs["args"])

        # Always send content-type
        if 'content-type' in kwargs_headers_keys:
            for k, v in headers.items():
                if k.lower() == 'content-type':
                    req_headers.pop(k, None)
        else:
            req_headers["Content-Type"] = "application/json"

        if req_headers:
            if "headers" in kwargs:
                kwargs["headers"].update(req_headers)
            else:
                kwargs["headers"] = req_headers

        return client._call_galaxy(url, *args, **kwargs)

    request.config = config
    return request
