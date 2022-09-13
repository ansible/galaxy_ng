"""Utility functions for AH tests."""

import logging
import random
import string


logger = logging.getLogger(__name__)


def generate_namespace(exclude=None):
    """ Create a valid random namespace string """

    # This should be a list of pre-existing namespaces
    if exclude is None:
        exclude = []

    def is_valid(ns):
        """ Assert namespace meets backend requirements """
        if ns is None:
            return False
        if ns in exclude:
            return False
        if len(namespace) < 3:
            return False
        if len(namespace) > 64:
            return False
        for char in namespace:
            if char not in string.ascii_lowercase + string.digits:
                return False

        return True

    namespace = None
    while not is_valid(namespace):
        namespace = ''
        namespace += random.choice(string.ascii_lowercase)
        for x in range(0, random.choice(range(3, 63))):
            namespace += random.choice(string.ascii_lowercase + string.digits + '_')

    return namespace


def get_all_namespaces(api_client=None, api_version='v3'):
    """ Create a list of namespaces visible to the client """

    assert api_client is not None, "api_client is a required param"
    namespaces = []
    next_page = f'/api/automation-hub/{api_version}/namespaces/'
    while next_page:
        resp = api_client(next_page)
        namespaces.extend(resp['data'])
        next_page = resp.get('links', {}).get('next')
    return namespaces


def generate_unused_namespace(api_client=None, api_version='v3'):
    """ Make a random namespace string that does not exist """

    assert api_client is not None, "api_client is a required param"
    existing = get_all_namespaces(api_client=api_client, api_version=api_version)
    existing = dict((x['name'], x) for x in existing)
    return generate_namespace(exclude=list(existing.keys()))


def create_unused_namespace(api_client=None):
    """ Make a namespace for testing """

    assert api_client is not None, "api_client is a required param"
    ns = generate_unused_namespace(api_client=api_client)
    payload = {'name': ns, 'groups': []}
    api_client('/api/automation-hub/v3/namespaces/', args=payload, method='POST')
    return ns
