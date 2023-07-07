"""test_community.py - Tests related to the community featureset.
"""

import json
import pytest

from urllib.parse import urlparse

from ..utils import (
    ansible_galaxy,
    build_collection,
    get_client,
    SocialGithubClient,
    create_user,
)
from ..utils.legacy import (
    clean_all_roles,
    cleanup_social_user,
    wait_for_v1_task,
)

from jsonschema import validate as validate_json

from ..schemas import (
    schema_objectlist,
)


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_community
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
    assert resp['GALAXY_FEATURE_FLAGS']['display_repositories'] is False
    assert resp['GALAXY_FEATURE_FLAGS']['execution_environments'] is False
    assert resp['GALAXY_FEATURE_FLAGS']['legacy_roles'] is True
    assert resp['GALAXY_FEATURE_FLAGS']['ai_deny_index'] is True
    assert resp['GALAXY_CONTAINER_SIGNING_SERVICE'] is None


@pytest.mark.deployment_community
def test_community_feature_flags(ansible_config):
    """Tests feature flags are correct"""

    config = ansible_config("anonymous_user")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=False
    )

    resp = api_client('/api/_ui/v1/feature-flags/', method='GET')
    assert resp['ai_deny_index'] is True
    assert resp['display_repositories'] is False
    assert resp['execution_environments'] is False
    assert resp['legacy_roles'] is True


@pytest.mark.deployment_community
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


@pytest.mark.deployment_community
def test_me_social(ansible_config):
    """ Tests a social authed user can see their user info """

    cleanup_social_user('gh01', ansible_config)

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('_ui/v1/me/')
        uinfo = resp.json()
        assert uinfo['username'] == cfg.get('username')


@pytest.mark.deployment_community
def test_social_redirect(ansible_config):
    """ Tests a social auth is redirected to / so the UI doesn't load some incorrect repo path."""

    # Github authorization redirects the client to ...
    #   <galaxy_ng>/complete/github/?code=d9e30acd653247152bf1&state=vdt3CD6wOtpFDX4PnLsBfi25v1o0f89E
    # Django responds with 302 redirect to /

    cleanup_social_user('gh01', ansible_config)

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        assert client.last_response.status_code == 302
        assert client.last_response.headers['Location'] == '/'


@pytest.mark.deployment_community
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


@pytest.mark.deployment_community
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


@pytest.mark.deployment_community
def test_social_auth_creates_group(ansible_config):

    cleanup_social_user('gh01', ansible_config)

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('_ui/v1/me/')
        uinfo = resp.json()
        assert uinfo['groups'][0]['name'] == 'namespace:gh01'


@pytest.mark.deployment_community
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


@pytest.mark.deployment_community
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


@pytest.mark.deployment_community
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


@pytest.mark.deployment_community
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


@pytest.mark.deployment_community
def test_list_collections_social(ansible_config):
    """ Tests a social authed user can see collections """

    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('v3/collections/')
        validate_json(instance=resp.json(), schema=schema_objectlist)


@pytest.mark.deployment_community
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

    # verify filtering in the way that the CLI does it
    resp = api_client(f'/api/v1/roles/?owner__username={github_user}')
    assert resp['count'] == 1
    assert resp['results'][0]['username'] == github_user
    roleid = resp['results'][0]['id']

    # validate the download_count was synced
    assert resp['results'][0]['download_count'] > 1

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


@pytest.mark.deployment_community
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

    # start the second sync to ensure second user doesn't get found
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
    resp2 = api_client(f'/api/v1/roles/?autocomplete={github_user}')
    assert resp2['count'] == resp['count']

    # cleanup
    cleanup_social_user(github_user, ansible_config)
    cleanup_social_user(github_user2, ansible_config)


@pytest.mark.deployment_community
def test_v1_role_pagination(ansible_config):
    """" Tests if v1 roles are auto-sorted by created """

    config = ansible_config("admin")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=True
    )

    def get_roles(page_size=1, order_by='created'):
        roles = []
        urls = []
        next_url = f'/api/v1/roles/?page_size={page_size}&order_by={order_by}'
        while next_url:
            urls.append(next_url)
            resp = api_client(next_url)
            roles.extend(resp['results'])
            next_url = resp['next']
            if next_url:
                o = urlparse(next_url)
                baseurl = o.scheme + '://' + o.netloc.replace(':80', '')
                next_url = next_url.replace(baseurl, '')

        return urls, roles

    # clean all roles ...
    clean_all_roles(ansible_config)

    # start the sync
    pargs = json.dumps({"limit": 10}).encode('utf-8')
    resp = api_client('/api/v1/sync/', method='POST', args=pargs)
    assert isinstance(resp, dict)
    assert resp.get('task') is not None
    wait_for_v1_task(resp=resp, api_client=api_client)

    # make tuples of created,id for all roles ...
    urls, all_roles = get_roles(page_size=1, order_by='created')
    roles = [[x['created'], x['id']] for x in all_roles]

    # make sure all 10 show up ...
    assert len(roles) == 10

    # make sure all pages were visited
    assert len(urls) == 10

    # make sure no duplicates found
    assert [x[1] for x in roles] == sorted(set([x[1] for x in roles]))

    # validate roles are ordered by created by default
    assert roles == sorted(roles)

    # repeat with ordered by name ...
    urls, all_roles = get_roles(page_size=1, order_by='name')
    roles = [x['name'] for x in all_roles]
    assert roles == sorted(roles)
    assert len(roles) == 10
    assert len(sorted(set(roles))) == 10

    # cleanup
    clean_all_roles(ansible_config)


@pytest.mark.deployment_community
def test_v1_role_tag_filter(ansible_config):
    """" Tests if v1 roles are auto-sorted by created """

    config = ansible_config("admin")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=True
    )

    def get_roles(page_size=1, order_by='created'):
        roles = []
        urls = []
        next_url = f'/api/v1/roles/?page_size={page_size}&order_by={order_by}'
        while next_url:
            urls.append(next_url)
            resp = api_client(next_url)
            roles.extend(resp['results'])
            next_url = resp['next']
            if next_url:
                o = urlparse(next_url)
                baseurl = o.scheme + '://' + o.netloc.replace(':80', '')
                next_url = next_url.replace(baseurl, '')

        return urls, roles

    # clean all roles ...
    clean_all_roles(ansible_config)

    # start the sync
    pargs = json.dumps({"limit": 10}).encode('utf-8')
    resp = api_client('/api/v1/sync/', method='POST', args=pargs)
    assert isinstance(resp, dict)
    assert resp.get('task') is not None
    wait_for_v1_task(resp=resp, api_client=api_client)

    # make tuples of created,id for all roles ...
    urls, all_roles = get_roles(page_size=1, order_by='created')

    # make a map of the tags
    tagmap = {}
    for role in all_roles:
        tags = role['summary_fields']['tags']
        for tag in tags:
            if tag not in tagmap:
                tagmap[tag] = []
            tagmap[tag].append(role['id'])

    # validate we can filter on every tag possible
    for tag, role_ids in tagmap.items():
        tresp = api_client(f'/api/v1/roles/?tag={tag}')
        assert tresp['count'] == len(role_ids)
        assert sorted(role_ids) == sorted([x['id'] for x in tresp['results']])

    # cleanup
    clean_all_roles(ansible_config)
