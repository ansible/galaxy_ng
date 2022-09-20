"""Utility functions for AH tests."""

import json
import logging

import requests

from ansible import context
from ansible.galaxy.api import GalaxyAPI
from ansible.galaxy.token import BasicAuthToken, GalaxyToken, KeycloakToken

from .urls import url_safe_join


logger = logging.getLogger(__name__)


def get_client(config, require_auth=True, request_token=True, headers=None):
    """Get an API client given a role."""

    return AnsibeGalaxyHttpClient(
        config=config,
        require_auth=require_auth,
        request_token=request_token,
        headers=headers
    )


class AnsibeGalaxyHttpClient:

    # the instantiated http client
    _galaxy_api_client = None

    # force the client to fetch a token?
    _request_token = False

    # force the client to do auth?
    _require_auth = False

    # the auth token
    _token = None

    # the auth'ed token type
    #   * keycloak -> bearer
    #   * galaxy -> token
    #   * basic -> user+pass
    _token_type = None

    def __init__(self, config=None, require_auth=True, request_token=True, headers=None):
        self._config = config
        self._require_auth = require_auth
        self._request_token = request_token
        self._headers = headers or {}

        # this is usually http://localhost:5001/api/automation-hub/
        self._server = self._config["url"]

        # this is usually a keycloak token request url
        self._auth_url = config.get("auth_url")

        # force the galaxy client lib to think the ignore certs kwarg was used
        # NOTE: this does not work with 2.12+
        context.CLIARGS = {"ignore_certs": True, "verbose": True}

        # negotiate for the auth token
        self.set_token()

        # instantiate the client
        self._galaxy_api_client = GalaxyAPI(
            None,
            "automation_hub",
            url=self._server,
            token=self.token
        )

        # Fix for 2.12+
        self._galaxy_api_client.validate_certs = False

    def __call__(self, url, *args, **kwargs):
        """
        Make the class callable so that tests won't
        need a complete refactor.
        """
        return self.request(url, *args, **kwargs)

    @property
    def config(self):
        return self._config

    @property
    def token(self):
        return self._token

    @property
    def token_type(self):
        return self._token_type

    def set_token(self):

        # start with the access token if known
        _token = self._config.get("token") or None
        self._token_type = 'config'

        # get some sort of token (keycloak/galaxy/basic)
        if self._request_token:

            if _token:
                # keycloak must have a unique auth url ...
                if self._auth_url:
                    # keycloak needs an access token to then return a bearer token
                    self._token = KeycloakToken(self._config["token"], auth_url=self._auth_url)
                    self._token_type = 'keycloak'
                else:
                    # django tokens - Authorization: token <token>
                    self._token = GalaxyToken(self._config["token"])
                    self._token_type = 'galaxy'
            else:
                # fallback to basic auth tokens
                self._token = BasicAuthToken(self._config["username"], self._config["password"])
                self._token_type = 'basic'

        # use basic auth
        elif self._require_auth:
            self._token = BasicAuthToken(self._config["username"], self._config["password"])
            self._token_type = 'basic'

        # anonymous auth
        else:
            self._token = None
            self._token_type = None

    def get_bearer_token(self):
        # payload
        #   grant_type=refresh_token&client_id=cloud-services&refresh_token=abcdefghijklmnopqrstuvwxyz1234567894
        # POST
        # auth_url
        #   'https://mocks-keycloak-ephemeral-ydabku.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com
        #       /auth/realms/redhat-external/protocol/openid-connect/token'

        payload = {
            'grant_type': 'refresh_token',
            'client_id': 'cloud-services',
            'refresh_token': self.config.get('token')
        }

        payload = {
            'grant_type': 'password',
            'client_id': 'cloud-services',
            'username': self.config.get('username'),
            'password': self.config.get('password'),
        }

        session = requests.Session()
        rr = session.post(
            self.config.get('auth_url'),
            headers={
                'User-Agent': 'ansible-galaxy/2.10.17 (Linux; python:3.10.6)'
            },
            data=payload,
            verify=False
        )

        return rr.json()['access_token']

    def request(
        self,
        url: str = None,
        args=None,
        headers: dict = None,
        method: str = 'GET',
        auth_required: bool = None,
    ) -> dict:

        """
        Make an api call with the upstream galaxy client lib from ansible core.
        """

        # default back to the auth_required value set at client init
        if auth_required is None:
            auth_required = self._require_auth

        # the callers are only sending partial urls most of the time
        url = url_safe_join(self._server, url)

        # detect args type and cast as needed
        is_json = False
        if isinstance(args, (dict, list)):
            args = json.dumps(args)
            is_json = True
        elif args and (args.startswith(b'{') or args.startswith(b'[')):
            args = json.dumps(json.loads(args))
            is_json = True

        # cast headers to dict if needed
        if headers is None:
            headers = {}

        # add in the initially configured headers
        if self._headers:
            headers.update(self._headers)

        # Always send content-type if json
        if is_json or args is None:
            for k in list(headers.keys()):
                if k.lower() == 'content-type':
                    headers.pop(k, None)
        if is_json:
            headers["Content-Type"] = "application/json"
        elif args is None:
            # fallback to text for NoneType
            headers["Content-Type"] = "application/text"

        # https://tinyurl.com/53m2scen
        return self._galaxy_api_client._call_galaxy(
            url,
            args=args,
            headers=headers,
            method=method,
            auth_required=auth_required,
        )
