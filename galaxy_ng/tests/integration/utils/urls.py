"""Utility functions for AH tests."""

import time

from urllib.parse import urljoin
from urllib.parse import urlparse

from ansible.galaxy.api import GalaxyError

from .errors import TaskWaitingTimeout


def test_url_safe_join():
    """Validate url_safe_join function."""
    testcases = [
        [
            'http://localhost:5001/api/<prefix>/',
            '/api/<prefix>/pulp/api/v3/docs/api.json',
            'http://localhost:5001/api/<prefix>/pulp/api/v3/docs/api.json',
        ],
        [
            'http://localhost:5001/api/<prefix>/',
            '/api/<prefix>/pulp/api/v3/',
            'http://localhost:5001/api/<prefix>/pulp/api/v3/'
        ],
        [

            'http://localhost:5001/api/<prefix>/',
            '/api/<prefix>/pulp/api/v3/repositories/ansible/ansible/',
            'http://localhost:5001/api/<prefix>/pulp/api/v3/repositories/ansible/ansible/'
        ],
        [
            'http://localhost:5001/api/<prefix>/',
            'http://localhost:5001/pulp/api/v3/tasks/<uuid>',
            'http://localhost:5001/pulp/api/v3/tasks/<uuid>'
        ],
        [
            'http://localhost:5001/api/<prefix>/',
            'http://localhost:5001/api/<prefix>//pulp/api/v3/tasks/<uuid>',
            'http://localhost:5001/api/<prefix>/pulp/api/v3/tasks/<uuid>'
        ],
        [
            'http://localhost:5001/api/<prefix>/',
            '/api/<prefix>/_ui/v1/collection-versions/?limit=10&offset=10&repository=published',
            (
                'http://localhost:5001/api/<prefix>/_ui/v1'
                + '/collection-versions/?limit=10&offset=10&repository=published'
            )
        ],
        [
            'http://localhost:5001/api/<prefix>/',
            (
                'v3/collections/autohubtest2/autohubtest2_teawkayi'
                + '/versions/1.0.0/move/staging/published/'
            ),
            (
                'http://localhost:5001/api/<prefix>/v3'
                + '/collections/autohubtest2/autohubtest2_teawkayi'
                + '/versions/1.0.0/move/staging/published/'
            )
        ]
    ]

    for idt, tc in enumerate(testcases):
        server = tc[0]
        url = tc[1]
        expected = tc[2]

        res = url_safe_join(server, url)
        assert res == expected, f"{res} != {expected} ... \n\t{server}\n\t{url}"


def url_safe_join(server, url):
    """
    Handle all the oddities of url joins
    """

    # parse both urls
    o = urlparse(server)
    o2 = urlparse(url)

    # strip the path from both urls
    server_path = o.path
    url_path = o2.path

    # remove double slashes
    if '//' in url_path:
        url_path = url_path.replace('//', '/')

    # append the query params if any to the url_path
    if o2.query:
        url_path = url_path.rstrip('/') + '/' + '?' + o2.query

    # start a new base url
    new_url = o.scheme + '://' + o.netloc

    # url contains the base path
    if not url.startswith(new_url) and url_path.startswith(server_path):
        return new_url + url_path

    # url contains the base url
    if url.startswith(new_url) and server_path in url_path:
        return (
            new_url
            + server_path.rstrip('/')
            + '/'
            + url_path.replace(server_path, '').lstrip('/')
        )

    # url path is a pulp root
    if url.startswith(new_url) and url_path.startswith('/pulp'):
        return new_url + url_path

    return urljoin(server.rstrip('/') + '/', url.lstrip('/'))


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
