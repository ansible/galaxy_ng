"""Utility functions for AH tests."""

import logging
import requests

from urllib.parse import urlparse


logger = logging.getLogger(__name__)


class UIClient:

    """ An HTTP client to mimic the UI """

    _rs = None

    def __init__(self, username=None, password=None, baseurl=None, authurl=None, config=None):
        self.username = username
        self.password = password
        self.baseurl = baseurl
        self.authurl = authurl
        self.config = config

        # default to config settings ...
        if self.config is not None and not self.username:
            self.username = self.config.get('username')
        if self.config is not None and not self.password:
            self.password = self.config.get('password')
        if self.config is not None and not self.baseurl:
            self.baseurl = self.config.get('url')
        if self.config is not None and not self.authurl:
            self.authurl = self.config.get('auth_url')

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
        self._rs = requests.Session()

        # GET the page to acquire the csrftoken
        self._rs.get(self.login_url)

        # parse the cookies
        cookies = self.cookies

        # now POST the credentials
        pheaders = {
            'Cookie': f"csrftoken={cookies['csrftoken']}",
            'X-CSRFToken': cookies['csrftoken']
        }
        self._rs.post(
            self.login_url,
            headers=pheaders,
            json={'username': self.username, 'password': self.password}
        )

    def logout(self, expected_code=None):

        if self._rs is None:
            raise Exception('client is not authenticated')

        # POST to the logout url with the cookie and sesionid
        cookies = self.cookies
        pheaders = {
            'Content-Type': 'application/json',
            'Cookie': f"csrftoken={cookies['csrftoken']}; sessionid={cookies['sessionid']}",
            'X-CSRFToken': cookies['csrftoken']
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

    def post(self, relative_url: str, payload: dict) -> requests.models.Response:
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
        resp = self._rs.post(self.baseurl + relative_url, json=payload, headers=pheaders)
        return resp

    def delete(self, relative_url: str) -> requests.models.Response:
        pheaders = {
            'Accept': 'application/json',
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


class SocialGithubClient:

    """ An HTTP client to mimic github social auth"""

    _rs = None
    _github_cookies = None
    _api_token = None
    sessionid = None
    csrftoken = None

    def __init__(
        self,
        username=None,
        password=None,
        baseurl=None,
        authurl=None,
        config=None,
        github_url=None,
        github_api_url=None
    ):
        self.username = username
        self.password = password
        self.baseurl = baseurl
        self.authurl = authurl
        self.github_url = github_url
        self.github_api_url = github_api_url
        self.config = config

        # default to config settings ...
        if self.config is not None and not self.username:
            self.username = self.config.get('username')
        if self.config is not None and not self.password:
            self.password = self.config.get('password')
        if self.config is not None and not self.baseurl:
            self.baseurl = self.config.get('url')
        if self.config is not None and not self.authurl:
            self.authurl = self.config.get('auth_url')
        if self.config is not None and not self.github_url:
            self.github_url = self.config.get('github_url')
        if self.config is not None and not self.github_api_url:
            self.github_api_url = self.config.get('github_api_url')

    @property
    def cookies(self):
        return dict(self._rs.cookies)

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, a, b, c):
        self.logout()

    def login(self):
        self._rs = requests.Session()

        # authenticate to github first
        rr1 = self._rs.post(
            f'{self.github_url}/session',
            data={'username': self.username, 'password': self.password}
        )
        self._github_cookies = dict(rr1.cookies)

        # The UX code obtains the login url from env vars ...
        #   const uiExternalLoginURI = process.env.UI_EXTERNAL_LOGIN_URI || '/login'
        # For the purposes of testing, we'll just construct a static version.
        client_id = 12345
        auth_url = f'{self.github_url}/login/oauth/authorize?scope=user&client_id={client_id}'

        # authorize the application
        rr2 = self._rs.get(
            auth_url,
            cookies=self._github_cookies,
        )

        # extract new csrftoken
        self.csrftoken = rr2.cookies['csrftoken']

        # extract sessionid
        self.sessionid = rr2.cookies['sessionid']

    def get_hub_token(self):

        if self._api_token is not None:
            return self._api_token

        # /api/v3/auth/token
        token_url = self.baseurl.rstrip('/') + '/v3/auth/token/'

        pheaders = {
            'Accept': 'application/json',
            'X-CSRFToken': self.csrftoken,
            'Cookie': f'csrftoken={self.csrftoken}; sessionid={self.sessionid}'
        }
        resp = self._rs.post(token_url, headers=pheaders)
        self._api_token = resp.json().get('token')
        return self._api_token

    def logout(self, expected_code=None):

        if self._rs is None:
            raise Exception('client is not authenticated')

    def get(self, relative_url: str = None, absolute_url: str = None) -> requests.models.Response:

        pheaders = {
            'Accept': 'application/json',
            'X-CSRFToken': self.csrftoken,
            'Cookie': f'csrftoken={self.csrftoken}; sessionid={self.sessionid}'
        }

        this_url = None
        if absolute_url:
            uri = urlparse(self.baseurl)
            this_url = f"{uri.scheme}://{uri.netloc}{absolute_url}"
        else:
            this_url = self.baseurl + relative_url

        # get the response
        resp = self._rs.get(this_url, headers=pheaders)
        return resp

    def delete(
        self,
        relative_url: str = None,
        absolute_url: str = None
    ) -> requests.models.Response:

        pheaders = {
            'Accept': 'application/json',
            'X-CSRFToken': self.csrftoken,
            'Cookie': f'csrftoken={self.csrftoken}; sessionid={self.sessionid}'
        }

        this_url = None
        if absolute_url:
            uri = urlparse(self.baseurl)
            this_url = f"{uri.scheme}://{uri.netloc}{absolute_url}"
        else:
            this_url = self.baseurl + relative_url

        # call delete
        resp = self._rs.delete(this_url, headers=pheaders)
        return resp

    def put(
        self,
        relative_url: str = None,
        absolute_url: str = None,
        data=None
    ) -> requests.models.Response:

        pheaders = {
            'Accept': 'application/json',
            'X-CSRFToken': self.csrftoken,
            'Cookie': f'csrftoken={self.csrftoken}; sessionid={self.sessionid}'
        }

        this_url = None
        if absolute_url:
            uri = urlparse(self.baseurl)
            this_url = f"{uri.scheme}://{uri.netloc}{absolute_url}"
        else:
            this_url = self.baseurl + relative_url

        # call put
        resp = self._rs.put(this_url, headers=pheaders, json=data)
        return resp

    def post(
        self,
        relative_url: str = None,
        absolute_url: str = None,
        data=None
    ) -> requests.models.Response:

        pheaders = {
            'Accept': 'application/json',
            'X-CSRFToken': self.csrftoken,
            'Cookie': f'csrftoken={self.csrftoken}; sessionid={self.sessionid}'
        }

        this_url = None
        if absolute_url:
            uri = urlparse(self.baseurl)
            this_url = f"{uri.scheme}://{uri.netloc}{absolute_url}"
        else:
            this_url = self.baseurl + relative_url

        # call post
        resp = self._rs.post(this_url, headers=pheaders, json=data)
        return resp
