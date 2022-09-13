import requests

from urllib.parse import urlparse


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
