"""test_community.py - Tests related to the community featureset.
"""

import json
import pytest
import requests
import subprocess

from ansible.galaxy.api import GalaxyError

from ..utils import get_client, wait_for_task


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_community
def test_community_collection_download_count_sync(ansible_config):
    """ Test collection download count sync command """

    # FIXME - once beta switches over, this test is no longer needed.

    config = ansible_config("admin")
    api_client = get_client(config, require_auth=True)

    # pick an upstream collection at random that does not exist locally ...
    sync_collection = None
    base_url = 'https://old-galaxy.ansible.com'
    next_url = base_url + '/api/v2/collections/'
    while next_url:
        rr = requests.get(next_url)
        ds = rr.json()
        for collection in ds['results']:
            namespace = collection['namespace']['name']
            name = collection['name']
            check_url = (
                '/api/v3/plugin/ansible/content/community'
                + f'/collections/index/{namespace}/{name}/'
            )
            try:
                api_client.request(check_url)
            except GalaxyError:
                sync_collection = (namespace, name)
                break

        if sync_collection:
            break

        if not ds['next_link']:
            break

        next_url = base_url + ds['next_link']

    assert sync_collection, "all upstream collections already exist on the system ... how?"

    # configure the remote
    resp = api_client.request('/api/pulp/api/v3/remotes/ansible/collection/')
    remotes = dict((x['name'], x) for x in resp['results'])
    community_remote_config = {
        'name': 'community',
        'url': 'https://old-galaxy.ansible.com/',
        'sync_dependencies': False,
        'requirements_file': json.dumps({'collections': ['.'.join(list(sync_collection))]}),
    }
    remote_task = api_client.request(
        remotes['community']['pulp_href'],
        method='PATCH',
        args=community_remote_config
    )
    wait_for_task(api_client, remote_task)

    # start the sync
    resp = api_client.request('/api/pulp/api/v3/repositories/ansible/ansible/')
    repos = dict((x['name'], x) for x in resp['results'])
    sync_payload = {'mirror': False, 'optimize': False, 'remote': remotes['community']['pulp_href']}
    sync_task = api_client.request(
        repos['community']['pulp_href'] + 'sync/',
        method='POST',
        args=sync_payload
    )

    # wait for the sync
    wait_for_task(api_client, sync_task)

    # run the django command
    pid = subprocess.run(
        'pulpcore-manager sync-collection-download-counts',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    assert pid.returncode == 0

    # check the counter in the api
    check_url = (
        '/api/v3/plugin/ansible/content/community/collections/'
        + f'index/{sync_collection[0]}/{sync_collection[1]}/'
    )
    check_resp = api_client.request(check_url)
    assert check_resp['download_count'] > 0, check_resp
