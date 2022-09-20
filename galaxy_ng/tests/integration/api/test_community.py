"""test_community.py - Tests related to the community featureset.
"""

import json
import time
import pytest

from ..utils import (
    get_client,
    SocialGithubClient
)

from jsonschema import validate as validate_json

from ..schemas import (
    schema_objectlist,
)


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.community_only
def test_community_settings(ansible_config):
    """Tests settings are correct"""

    config = ansible_config("anonymous_user")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=False
    )

    resp = api_client('/api/_ui/v1/settings/', method='GET')

    assert resp['GALAXY_AUTH_LDAP_ENABLED'] is None
    assert resp['GALAXY_AUTO_SIGN_COLLECTIONS'] is False
    assert resp['GALAXY_REQUIRE_CONTENT_APPROVAL'] is False
    assert resp['GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL'] is False
    assert resp['GALAXY_SIGNATURE_UPLOAD_ENABLED'] is False
    assert resp['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS'] is True
    assert resp['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD'] is True


@pytest.mark.community_only
def test_me_anonymous(ansible_config):
    """Tests anonymous user is detected correctly"""

    config = ansible_config("anonymous_user")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=False
    )

    resp = api_client('/api/_ui/v1/me/', method='GET')

    assert resp['username'] == ""
    assert resp['id'] is None
    assert resp['is_anonymous'] is True
    assert resp['is_superuser'] is False


@pytest.mark.community_only
def test_me_social(ansible_config):
    """ Tests a social authed user can see their user info """

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('_ui/v1/me/')
        uinfo = resp.json()
        assert uinfo['username'] == cfg.get('username')


@pytest.mark.skip(reason='waiting for rbac')
@pytest.mark.community_only
def test_social_auth_creates_group(ansible_config):

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('_ui/v1/me/')
        uinfo = resp.json()
        assert uinfo['groups'][0]['name'] == 'github:gh01'


@pytest.mark.community_only
def test_social_auth_creates_legacynamespace(ansible_config):

    # cleanup the namespace first
    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )
    resp = admin_client('/api/v1/namespaces/?name=gh01', method='GET')
    if resp['count'] > 0:
        for result in resp['results']:
            ns_url = f"/api/v1/namespaces/{result['id']}/"
            try:
                admin_client(ns_url, method='DELETE')
            except Exception:
                pass
    resp = admin_client('/api/v1/namespaces/?name=gh01', method='GET')
    assert resp['count'] == 0

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('v1/namespaces/?name=gh01')
        result = resp.json()
        assert result['count'] == 1
        assert result['results'][0]['name'] == 'gh01'

        # the user should have been added as an owner on the namespace
        assert result['results'][0]['summary_fields']['owners'][0]['username'] == 'gh01'


@pytest.mark.community_only
def test_update_legacynamespace_owners(ansible_config):

    # cleanup the namespace first
    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )
    resp = admin_client('/api/v1/namespaces/?name=gh01', method='GET')
    if resp['count'] > 0:
        for result in resp['results']:
            ns_url = f"/api/v1/namespaces/{result['id']}/"
            try:
                admin_client(ns_url, method='DELETE')
            except Exception:
                pass
    resp = admin_client('/api/v1/namespaces/?name=gh01', method='GET')
    assert resp['count'] == 0

    # make sure user2 is created
    cfg = ansible_config('github_user_2')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('_ui/v1/me/')
        uinfo2 = resp.json()

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:

        # find the namespace
        ns_resp = client.get('v1/namespaces/?name=gh01')
        ns_result = ns_resp.json()
        ns_id = ns_result['results'][0]['id']
        ns_url = f'v1/namespaces/{ns_id}/'
        owners_url = ns_url + 'owners/'

        # assemble payload
        new_owners = {'owners': [{'id': uinfo2['id']}]}

        # put the payload
        update_resp = client.put(owners_url, data=new_owners)
        assert update_resp.status_code == 200

        # get the new data
        ns_resp2 = client.get(owners_url)
        owners2 = ns_resp2.json()
        owners2_usernames = [x['username'] for x in owners2]
        assert 'gh01' not in owners2_usernames
        assert uinfo2['username'] in owners2_usernames


@pytest.mark.community_only
def test_list_collections_anonymous(ansible_config):
    """Tests whether collections can be browsed anonymously"""

    config = ansible_config("anonymous_user")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=False
    )

    resp = api_client('/api/v3/collections/', method='GET')
    validate_json(instance=resp, schema=schema_objectlist)


@pytest.mark.community_only
def test_list_collections_social(ansible_config):
    """ Tests a social authed user can see collections """

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('v3/collections/')
        validate_json(instance=resp.json(), schema=schema_objectlist)


@pytest.mark.community_only
def test_v1_sync_with_user_and_limit(ansible_config):
    """" Tests if v1 sync accepts a user&limit arg """

    config = ansible_config("admin")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=True
    )

    github_user = '030'
    pargs = json.dumps({"github_user": "030", "limit": 1}).encode('utf-8')

    # delete any pre-existing roles from the user
    pre_existing = []
    next_url = f'/api/v1/roles/?owner__username={github_user}'
    while next_url:
        resp = api_client(next_url)
        pre_existing.extend(resp['results'])
        if resp['next'] is None:
            break
        next_url = resp['next']
    if pre_existing:
        for pe in pre_existing:
            role_id = pe['id']
            role_url = f'/api/v1/roles/{role_id}/'
            try:
                resp = api_client(role_url, method='DELETE')
            except Exception:
                pass

    # start the sync
    resp = api_client('/api/v1/sync/', method='POST', args=pargs)
    assert isinstance(resp, dict)
    assert resp.get('task') is not None

    task_id = resp['task']

    # poll till done or timeout
    poll_url = f'/api/v1/tasks/{task_id}/'
    state = None
    counter = 0
    while state is None or state == 'RUNNING' and counter <= 100:
        counter += 1
        task_resp = api_client(poll_url, method='GET')
        state = task_resp['results'][0]['state']
        if state != 'RUNNING':
            break
        time.sleep(.5)
    assert state == 'SUCCESS'

    resp = api_client(f'/api/v1/roles/?owner__username={github_user}')
    assert resp['count'] == 1
    assert resp['results'][0]['username'] == github_user
    roleid = resp['results'][0]['id']

    # validate the versions endpoint
    versions_url = f'/api/v1/roles/{roleid}/versions/'
    vresp = api_client(versions_url)
    assert vresp['count'] > 0

    # validate the content endpoint
    content_url = f'/api/v1/roles/{roleid}/content/'
    cresp = api_client(content_url)
    assert 'readme' in cresp
    assert 'readme_html' in cresp

    # cleanup
    role_id = resp['results'][0]['id']
    role_url = f'/api/v1/roles/{role_id}/'
    try:
        resp = api_client(role_url, method='DELETE')
    except Exception:
        pass
    resp = api_client(f'/api/v1/roles/?owner__username={github_user}')
    assert resp['count'] == 0
