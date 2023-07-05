"""Utility functions for AH tests."""

import logging
import requests
import re
import html

from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)


class UIClient:

    """ An HTTP client to mimic the UI """

    _rs = None

    def __init__(self,
                 username=None,
                 password=None,
                 baseurl=None,
                 authurl=None,
                 config=None,
                 auth_backend=None):
        self.username = username
        self.password = password
        self.baseurl = baseurl
        self.authurl = authurl
        self.config = config
        self.auth_backend = auth_backend

        # default to config settings ...
        if self.config is not None and not self.username:
            self.username = self.config.get('username')
        if self.config is not None and not self.password:
            self.password = self.config.get('password')
        if self.config is not None and not self.baseurl:
            self.baseurl = self.config.get('url')
        if self.config is not None and not self.authurl:
            self.authurl = self.config.get('auth_url')
        if self.config is not None and not self.auth_backend:
            self.auth_backend = self.config.get('auth_backend')

        self.login_url = self.baseurl + '_ui/v1/auth/login/'
        self.logout_url = self.baseurl + '_ui/v1/auth/logout/'

    @property
    def cookies(self):
        return dict(self._rs.cookies)

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, a, b, c):
        self.logout()

    def login(self):
        if self.auth_backend == "keycloak":
            return self.keycloak_login()
        else:
            return self.galaxy_login()

    def galaxy_login(self):
        self._rs = requests.Session()
        self._rs.verify = False

        # GET the page to acquire the csrftoken
        self._rs.get(self.login_url)

        # parse the cookies
        cookies = self.cookies

        # now POST the credentials
        pheaders = {
            'Cookie': f"csrftoken={cookies['csrftoken']}",
            'X-CSRFToken': cookies['csrftoken'],
            'Referer': self.login_url,
        }
        resp = self._rs.post(
            self.login_url,
            headers=pheaders,
            json={'username': self.username, 'password': self.password}
        )

        # assert that the login succeeded
        assert resp.status_code in (200, 204)

    def keycloak_login(self):
        self._rs = requests.Session()

        # Get the keycloak login page
        resp = self._rs.get(
            self.baseurl.split("/api/")[0] + "/login/",
            allow_redirects=True,
        )

        # assert that the keycloak login page loaded correctly
        assert resp.status_code == 200

        # Parse the login url out of the keycloak html form
        url = re.search(b'action="([^"]*)"', resp.content)

        # Log the user in
        resp = self._rs.post(
            html.unescape(unquote(url.group(1).decode("utf-8"))),
            data={
                'username': self.username,
                'password': self.password,
                'credentialId': ''
            },
            allow_redirects=True,
        )

        # assert that the login succeeded
        assert resp.status_code in (200, 204)

    def logout(self, expected_code=None):
        if self._rs is None:
            raise Exception('client is not authenticated')

        # POST to the logout url with the cookie and sesionid
        cookies = self.cookies
        pheaders = {
            'Content-Type': 'application/json',
            'Cookie': f"csrftoken={cookies['csrftoken']}; sessionid={cookies['sessionid']}",
            'X-CSRFToken': cookies['csrftoken'],
            'Referer': self.login_url,
        }
        res = self._rs.post(self.logout_url, json={}, headers=pheaders)

        if expected_code is not None:
            if res.status_code != expected_code:
                raise Exception(f'logout status code was not {expected_code}')

    def get(self, relative_url: str = None, absolute_url: str = None) -> requests.models.Response:

        pheaders = {
            'Accept': 'application/json',
        }

        # send cookies whenever possible ...
        if self.cookies is not None:
            cookie = []
            if self.cookies.get('csrftoken'):
                cookie.append(f"csrftoken={self.cookies['csrftoken']}")
            if self.cookies.get('sessionid'):
                cookie.append(f"sessionid={self.cookies['sessionid']}")
            pheaders['Cookie'] = '; '.join(cookie)

        this_url = None
        if absolute_url:
            uri = urlparse(self.baseurl)
            this_url = f"{uri.scheme}://{uri.netloc}{absolute_url}"
        else:
            this_url = self.baseurl + relative_url

        # get the response
        resp = self._rs.get(this_url, headers=pheaders)
        return resp

    def get_paginated(self, relative_url: str = None, absolute_url: str = None) -> list:
        """Iterate through all results in a paginated queryset"""
        if absolute_url:
            resp = self.get(absolute_url=absolute_url)
        else:
            resp = self.get(relative_url)

        ds = resp.json()
        key = 'results'
        if 'data' in ds:
            key = 'data'
            results = ds['data']
        else:
            results = ds['results']

        next_url = ds['links']['next']
        while next_url:
            if next_url.startswith(urlparse(self.baseurl).path):
                next_resp = self.get(absolute_url=next_url)
            else:
                next_resp = self.get(next_url)
            _ds = next_resp.json()
            results.extend(_ds[key])
            next_url = _ds['links']['next']

        return results

    def post(self, relative_url: str, payload: dict) -> requests.models.Response:
        pheaders = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Referer': self.login_url
        }

        # send cookies whenever possible ...
        if self.cookies is not None:
            cookie = []
            if self.cookies.get('csrftoken'):
                pheaders['X-CSRFToken'] = self.cookies['csrftoken']
                cookie.append(f"csrftoken={self.cookies['csrftoken']}")
            if self.cookies.get('sessionid'):
                cookie.append(f"sessionid={self.cookies['sessionid']}")
            pheaders['Cookie'] = '; '.join(cookie)

        # get the response
        resp = self._rs.post(self.baseurl + relative_url, json=payload, headers=pheaders)
        return resp

    def put(self, relative_url: str, payload: dict) -> requests.models.Response:
        pheaders = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        # send cookies whenever possible ...
        if self.cookies is not None:
            cookie = []
            if self.cookies.get('csrftoken'):
                pheaders['X-CSRFToken'] = self.cookies['csrftoken']
                cookie.append(f"csrftoken={self.cookies['csrftoken']}")
            if self.cookies.get('sessionid'):
                cookie.append(f"sessionid={self.cookies['sessionid']}")
            pheaders['Cookie'] = '; '.join(cookie)

        # get the response
        resp = self._rs.put(self.baseurl + relative_url, json=payload, headers=pheaders)
        return resp

    def delete(self, relative_url: str) -> requests.models.Response:
        pheaders = {
            'Accept': 'application/json',
            'Referer': self.login_url
        }

        # send cookies whenever possible ...
        if self.cookies is not None:
            cookie = []
            if self.cookies.get('csrftoken'):
                pheaders['X-CSRFToken'] = self.cookies['csrftoken']
                cookie.append(f"csrftoken={self.cookies['csrftoken']}")
            if self.cookies.get('sessionid'):
                cookie.append(f"sessionid={self.cookies['sessionid']}")
            pheaders['Cookie'] = '; '.join(cookie)

        # get the response
        resp = self._rs.delete(self.baseurl + relative_url, headers=pheaders)
        return resp
