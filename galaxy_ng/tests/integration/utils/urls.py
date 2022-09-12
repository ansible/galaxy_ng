"""Utility functions for AH tests."""

import os
import time

from urllib.parse import urljoin
from urllib.parse import urlparse

from ansible.galaxy.api import GalaxyError

from .errors import TaskWaitingTimeout


def test_url_safe_join():
    """Validate url_safe_join function."""
    this_file = __file__
    this_dir = os.path.dirname(this_file)
    fn = os.path.join(this_dir, 'testurls.txt')
    with open(fn, 'r') as f:
        fdata = f.read()
    flines = fdata.split('\n')
    for fline in flines:
        if not fline.strip():
            continue
        if fline.startswith('"""'):
            continue
        parts = fline.split(',')

        server = parts[0]
        url = parts[1]
        expected = parts[2]

        res = url_safe_join(server, url) == expected
        assert url_safe_join(server, url) == expected, f"{res} != {expected}"


def url_safe_join(server, url):
    """
    Handle all the oddities of url joins
    """

    def validate(this_url):
        if 'automation-hub' in this_url and '/pulp' in this_url:
            raise Exception('bad url join on {server} {url}')
        return this_url

    # parse both urls
    o = urlparse(server)
    o2 = urlparse(url)

    # strip the path from both urls
    server_path = o.path
    url_path = o2.path.replace(server_path, '')

    # append the query params if any to the url_path
    if o2.query:
        url_path = url_path.rstrip('/') + '/' + '?' + o2.query

    # start a new base url
    new_url = o.scheme + '://' + o.netloc

    # Task urls are coming back malformed ...
    # http://localhost:5001/api/automation-hub//pulp/api/v3/tasks/b7218b84-e9e3-4995-8c9e-0a170558037d
    # http://localhost:5001pulp/api/v3/tasks/675ed6d5-a76a-4964-a9d2-9a0c941edca4
    if '/pulp' in url_path:
        url_path = url_path.replace(server_path, '')
    if url_path.startswith('pulp/'):
        url_path = '/' + url_path

    if not url_path:
        return validate(new_url + server_path)
    elif url_path.startswith(server_path):
        return validate(urljoin(new_url, url_path))
    elif url_path.startswith('v3/') or url_path.startswith('_ui/'):
        return validate(new_url + urljoin(server_path.rstrip('/') + '/', url_path.lstrip('/')))
    elif url_path.startswith('/pulp/'):
        return validate(new_url.rstrip('/') + '/' + url_path.lstrip('/'))
    elif url_path.startswith('/api/v3') and server_path == '/api/automation-hub/':
        return validate(new_url + url_path.replace('/api/', server_path))
    elif url_path.startswith('content/'):
        # /api/automation-hub/content/<str:path>/v3/collections/<str:namespace>/<str:name>/versions/
        return validate(new_url + urljoin(server_path, url_path))
    elif url_path.startswith('collections/'):
        # /api/automation-hub/content/<str:path>/v3/collections/<str:namespace>/<str:name>/versions/
        return validate(new_url + urljoin(server_path, 'v3/' + url_path))

    # Fallback ...
    if url.startswith('http'):
        return url
    return urljoin(server, url)


def wait_for_url(api_client, url, timeout_sec=30):
    """Wait until url stops returning a 404."""
    ready = False
    res = None
    wait_until = time.time() + timeout_sec
    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        try:
            res = api_client(url, method="GET")
        except GalaxyError as e:
            if "404" not in str(e):
                raise
            time.sleep(0.5)
        else:
            ready = True
    return res
