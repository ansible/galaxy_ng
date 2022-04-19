"""test_galaxykit.py - Test galaxykit integration.


"""
import json
import pytest
import random
import string
import subprocess
import time

from ansible.galaxy.api import GalaxyError

from ..utils import get_client
from ..utils import get_all_collections_by_repo
from ..utils import get_all_repository_collection_versions
from ..utils import wait_for_task


pytestmark = pytest.mark.qa  # noqa: F821

'''
[jtanner@p1 galaxy_ng]$ /tmp/gng_testing/bin/galaxykit --help
usage: galaxykit [-h] [-i] [-u USERNAME] [-p PASSWORD] [-t TOKEN] [-a AUTH_URL] [-c] [-s SERVER] kind operation [rest ...]

positional arguments:
  kind                  Kind of API content to operate against (user, group, namespace)
  operation
  rest

options:
  -h, --help            show this help message and exit
  -i, --ignore
  -u USERNAME, --username USERNAME
  -p PASSWORD, --password PASSWORD
  -t TOKEN, --token TOKEN
  -a AUTH_URL, --auth-url AUTH_URL
  -c, --ignore-certs    Ignore invalid SSL certificates
  -s SERVER, --server SERVER
'''

def get_galaxykit_base_cmd(config):
    kwargs = {}
    kwargs['--server'] = config.get('url')
    if config.get('auth_url'):
        kwargs['--auth-url'] = config.get('auth_url')
    kwargs['--username'] = config.get('username')
    if config.get('password'):
        kwargs['--password'] = config.get('password')
    if config.get('token'):
        kwargs['--token'] = config.get('token')

    cmd = 'galaxykit -i'
    for k,v in kwargs.items():
        cmd += ' ' + k + '=' + v

    return cmd


@pytest.mark.galaxyapi_smoke
@pytest.mark.galaxykit
def test_galaxykit_namespace_management(ansible_config):
    """Tests whether a colleciton can be deleted"""

    config = ansible_config("ansible_partner")
    basecmd = get_galaxykit_base_cmd(config)

    ns = 'foozbar'

    # create a namespace
    create_cmd = basecmd + f' namespace create {ns}'
    pid = subprocess.run(create_cmd, shell=True)
    assert pid.returncode == 0

    # make sure it was created
    get_cmd = basecmd + f' namespace get {ns}'
    pid = subprocess.run(get_cmd, shell=True, stdout=subprocess.PIPE)
    assert pid.returncode == 0
    ds = json.loads(pid.stdout.decode('utf-8'))
    assert ds['name'] == ns

    # delete it
    del_cmd = basecmd + f' namespace delete {ns}'
    pid = subprocess.run(del_cmd, shell=True, stdout=subprocess.PIPE)
    assert pid.returncode == 0

    # make sure it is gone
    pid = subprocess.run(get_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert pid.returncode == 1


@pytest.mark.galaxyapi_smoke
@pytest.mark.galaxykit
@pytest.mark.testme
def test_galaxykit_collection_management(ansible_config):
    """Tests whether a colleciton can be deleted"""

    config = ansible_config("ansible_partner")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )
    basecmd = get_galaxykit_base_cmd(config)

    rs = random.choice(string.ascii_lowercase) + random.choice(string.ascii_lowercase) + random.choice(string.digits)
    ns = 'testspace' + rs
    cn = 'testcollection' + rs
    cv = '1.0.0'

    pid = subprocess.run(basecmd + f' namespace create {ns}', shell=True)
    assert pid.returncode == 0

    # Cleanup
    del_cmd = basecmd + f' -i collection delete {ns} {cn}'
    pid = subprocess.run(del_cmd, shell=True)

    # Create it
    upload_cmd = basecmd + f' -i collection upload {ns} {cn}'
    pid = subprocess.run(upload_cmd, shell=True, stdout=subprocess.PIPE)
    assert pid.returncode == 0

    # Certify it
    move_cmd = basecmd + f' -i collection move {ns} {cn}'
    pid = subprocess.run(move_cmd, shell=True, stdout=subprocess.PIPE)
    assert pid.returncode == 0

    # Check that it exists
    info_cmd = basecmd + f' -i collection info {ns} {cn} {cv}'
    pid = subprocess.run(info_cmd, shell=True, stdout=subprocess.PIPE)
    assert pid.returncode == 0
    ds = json.loads(pid.stdout.decode('utf-8'))
    assert ds['namespace']['name'] == ns
    assert ds['name'] == cn
    assert ds['version'] == cv

    # Verify through cli client ...
    collections1 = get_all_collections_by_repo(api_client)
    published1 = list(collections1['published'].keys())
    assert (ns, cn, cv) in published1

    # Delete the collection
    pid = subprocess.run(del_cmd, shell=True, stdout=subprocess.PIPE)
    assert pid.returncode == 0
    import epdb; epdb.st()

    time.sleep(10)

    # Ensure it's gone
    pid = subprocess.run(info_cmd, shell=True, stdout=subprocess.PIPE)
    #assert pid.returncode == 1
    import epdb; epdb.st()

    # Check via the cli client ...
    collections2 = get_all_collections_by_repo(api_client)
    published2 = list(collections2['published'].keys())
    assert (ns, cn, cv) not in published2
    import epdb; epdb.st()
