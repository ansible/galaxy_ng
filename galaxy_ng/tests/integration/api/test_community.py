"""test_community.py - Tests related to the community featureset.
"""

import json
import time
import pytest

from ..utils import (
    ansible_galaxy,
    build_collection,
    cleanup_namespace,
    get_client,
    SocialGithubClient,
    delete_group,
    create_user,
    delete_user
)

from jsonschema import validate as validate_json

from ..schemas import (
    schema_objectlist,
)


pytestmark = pytest.mark.qa  # noqa: F821


def cleanup_social_user(username, ansible_config):
    """ Should delete everything related to a social auth'ed user. """

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    # delete any pre-existing roles from the user
    pre_existing = []
    next_url = f'/api/v1/roles/?owner__username={username}'
    while next_url:
        resp = admin_client(next_url)
        pre_existing.extend(resp['results'])
        if resp['next'] is None:
            break
        next_url = resp['next']
    if pre_existing:
        for pe in pre_existing:
            role_id = pe['id']
            role_url = f'/api/v1/roles/{role_id}/'
            try:
                resp = admin_client(role_url, method='DELETE')
            except Exception:
                pass

    # cleanup the v1 namespace
    resp = admin_client(f'/api/v1/namespaces/?name={username}', method='GET')
    if resp['count'] > 0:
        for result in resp['results']:
            ns_url = f"/api/v1/namespaces/{result['id']}/"
            try:
                admin_client(ns_url, method='DELETE')
            except Exception:
                pass
    resp = admin_client(f'/api/v1/namespaces/?name={username}', method='GET')
    assert resp['count'] == 0

    # cleanup the v3 namespace
    cleanup_namespace(username, api_client=get_client(config=ansible_config("admin")))

    # cleanup the group
    delete_group(username, api_client=get_client(config=ansible_config("admin")))
    delete_group('github:' + username, api_client=get_client(config=ansible_config("admin")))

    # cleanup the user
    delete_user(username, api_client=get_client(config=ansible_config("admin")))


def wait_for_v1_task(task_id=None, resp=None, api_client=None):

    if task_id is None:
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

    cleanup_social_user('gh01', ansible_config)

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('_ui/v1/me/')
        uinfo = resp.json()
        assert uinfo['username'] == cfg.get('username')


@pytest.mark.community_only
def test_me_social_with_precreated_user(ansible_config):
    """ Make sure social auth associates to the correct username """

    cleanup_social_user('gh01', ansible_config)

    # set the social config ...
    cfg = ansible_config('github_user_1')

    # make a normal user first
    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )
    create_user(cfg.get('username'), None, api_client=admin_client)

    # login and verify matching username
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('_ui/v1/me/')
        uinfo = resp.json()
        assert uinfo['username'] == cfg.get('username')


@pytest.mark.community_only
def test_me_social_with_v1_synced_user(ansible_config):
    """ Make sure social auth associates to the correct username """

    username = 'geerlingguy'
    cleanup_social_user(username, ansible_config)

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    # v1 sync the user's roles and namespace ...
    pargs = json.dumps({"github_user": username, "limit": 1}).encode('utf-8')
    resp = admin_client('/api/v1/sync/', method='POST', args=pargs)
    wait_for_v1_task(resp=resp, api_client=admin_client)

    # set the social config ...
    cfg = ansible_config(username)

    # login and verify matching username
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('_ui/v1/me/')
        assert resp.status_code == 200
        uinfo = resp.json()
        assert uinfo['username'] == cfg.get('username')


@pytest.mark.community_only
def test_social_auth_creates_group(ansible_config):

    cleanup_social_user('gh01', ansible_config)

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('_ui/v1/me/')
        uinfo = resp.json()
        assert uinfo['groups'][0]['name'] == 'github:gh01'


@pytest.mark.community_only
def test_social_auth_creates_v3_namespace(ansible_config):

    cleanup_social_user('gh01', ansible_config)

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:

        resp = client.get('v3/namespaces/?name=gh01')
        result = resp.json()
        assert result['meta']['count'] == 1
        assert result['data'][0]['name'] == 'gh01'

        # make a collection
        collection = build_collection(
            use_orionutils=False,
            namespace='gh01',
            name='mystuff',
            version='1.0.0'
        )

        # verify the user can publish to the namespace ...
        ansible_galaxy(
            f"collection publish {collection.filename}",
            ansible_config=ansible_config("github_user_1"),
            force_token=True,
            token=client.get_hub_token()
        )


@pytest.mark.community_only
def test_social_auth_creates_legacynamespace(ansible_config):

    cleanup_social_user('gh01', ansible_config)

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

    cleanup_social_user('gh01', ansible_config)

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
    cleanup_social_user(github_user, ansible_config)

    # start the sync
    pargs = json.dumps({"github_user": "030", "limit": 1}).encode('utf-8')
    resp = api_client('/api/v1/sync/', method='POST', args=pargs)
    assert isinstance(resp, dict)
    assert resp.get('task') is not None
    wait_for_v1_task(resp=resp, api_client=api_client)

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
    cleanup_social_user(github_user, ansible_config)


@pytest.mark.community_only
def test_v1_autocomplete_search(ansible_config):
    """" Tests if v1 sync accepts a user&limit arg """

    config = ansible_config("admin")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=True
    )

    github_user = 'geerlingguy'
    github_user2 = '030'
    cleanup_social_user(github_user, ansible_config)
    cleanup_social_user(github_user2, ansible_config)

    # start the sync
    pargs = json.dumps({"github_user": github_user, "limit": 10}).encode('utf-8')
    resp = api_client('/api/v1/sync/', method='POST', args=pargs)
    assert isinstance(resp, dict)
    assert resp.get('task') is not None
    wait_for_v1_task(resp=resp, api_client=api_client)

    # start the second sync
    pargs = json.dumps({"github_user": github_user2, "limit": 10}).encode('utf-8')
    resp = api_client('/api/v1/sync/', method='POST', args=pargs)
    assert isinstance(resp, dict)
    assert resp.get('task') is not None
    wait_for_v1_task(resp=resp, api_client=api_client)

    # query by user
    resp = api_client(f'/api/v1/roles/?owner__username={github_user}')
    assert resp['count'] > 0
    usernames = sorted(set([x['username'] for x in resp['results']]))
    assert usernames == [github_user]

    # validate autocomplete search only finds the relevant roles
    sresp = api_client(f'/api/v1/roles/?autocomplete={github_user}')
    assert sresp['count'] == resp['count']

    # cleanup
    cleanup_social_user(github_user, ansible_config)
