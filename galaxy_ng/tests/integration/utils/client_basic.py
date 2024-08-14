import json
import requests
from urllib.parse import urlparse, urljoin

from galaxykit.client import GalaxyClient
from galaxykit.utils import GalaxyClientError


class BasicAuthClient(GalaxyClient):
    '''Simplified basic auth through galaxykit.'''

    def __init__(self, galaxy_root, username, password):
        self.galaxy_root = galaxy_root
        self.username = username
        self.password = password
        self.auth = (self.username, self.password)

    def _payload(self, *args, **kwargs):
        return self._http(*args, **kwargs)

    def _http(self, method, path, *args, **kwargs):

        # relative vs absolute url paths ...
        if not path.startswith('/'):
            url = urljoin(self.galaxy_root.rstrip("/") + "/", path)
        else:
            parsed = urlparse(self.galaxy_root)
            url = self.galaxy_root.replace(parsed.path, '')
            url = urljoin(url.rstrip('/'), path)

        kwargs['auth'] = self.auth
        kwargs['verify'] = False

        # munge body back to json if possible ...
        if kwargs.get('body'):
            try:
                kwargs['json'] = json.loads(kwargs['body'])
                kwargs.pop('body')
            except Exception:
                kwargs['data'] = kwargs['body']
                kwargs.pop('body')

        # not all endpoints return json
        want_json = True
        if 'want_json' in kwargs:
            want_json = kwargs['want_json']
            kwargs.pop('want_json')

        func = getattr(requests, method)
        rr = func(url, **kwargs)

        try:
            if want_json:
                return rr.json()
            return rr.text
        except Exception:
            raise GalaxyClientError(rr.text, rr.status_code)
