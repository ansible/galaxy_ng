"""test_community.py - Tests related to the community featureset.
"""

import json
import pytest
import random
import string

from ..utils import (
    get_client,
    SocialGithubClient,
    GithubAdminClient,
    cleanup_namespace,
)
from ..utils.legacy import (
    cleanup_social_user,
    wait_for_v1_task,
)


pytestmark = pytest.mark.qa  # noqa: F821


def extract_default_config(ansible_config):
    base_cfg = ansible_config('github_user_1')
    cfg = {}
    cfg['token'] = None
    cfg['url'] = base_cfg.get('url')
    cfg['auth_url'] = base_cfg.get('auth_url')
    cfg['github_url'] = base_cfg.get('github_url')
    cfg['github_api_url'] = base_cfg.get('github_api_url')
    return cfg


@pytest.mark.deployment_community
def test_admin_can_import_legacy_roles(ansible_config):

    github_user = 'jctannerTEST'
    github_repo = 'role1'
    cleanup_social_user(github_user, ansible_config)
    cleanup_social_user(github_user.lower(), ansible_config)

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    # do an import with the admin ...
    payload = {
        'github_repo': github_repo,
        'github_user': github_user,
    }
    resp = admin_client('/api/v1/imports/', method='POST', args=payload)
    assert resp['results'][0]['pulp_id'] is not None, resp
    task_id = resp['results'][0]['id']
    res = wait_for_v1_task(task_id=task_id, api_client=admin_client, check=False)

    # it should have failed because of the missing v1+v3 namespaces ...
    assert res['results'][0]['state'] == 'FAILED', res

    # make the legacy namespace
    ns_payload = {
        'name': github_user
    }
    resp = admin_client('/api/v1/namespaces/', method='POST', args=ns_payload)
    assert resp['name'] == github_user, resp
    assert not resp['summary_fields']['owners'], resp
    assert not resp['summary_fields']['provider_namespaces'], resp
    v1_id = resp['id']

    # make the v3 namespace
    v3_payload = {
        'name': github_user.lower(),
        'groups': [],
    }
    resp = admin_client('/api/_ui/v1/namespaces/', method='POST', args=v3_payload)
    assert resp['name'] == github_user.lower(), resp
    v3_id = resp['id']

    # bind the v3 namespace to the v1 namespace
    v3_bind = {
        'id': v3_id
    }
    admin_client(f'/api/v1/namespaces/{v1_id}/providers/', method='POST', args=v3_bind)

    # check the providers ...
    resp = admin_client(f'/api/v1/namespaces/{v1_id}/providers/')
    assert resp[0]['id'] == v3_id, resp

    # try to import again ...
    resp = admin_client('/api/v1/imports/', method='POST', args=payload)
    assert resp['results'][0]['pulp_id'] is not None, resp
    task_id = resp['results'][0]['id']
    res = wait_for_v1_task(task_id=task_id, api_client=admin_client, check=False)
    assert res['results'][0]['state'] == 'SUCCESS', res


@pytest.mark.skip(reason="not ready yet")
@pytest.mark.deployment_community
def test_social_auth_v3_rbac_workflow(ansible_config):

    # cleanup_social_user('gh01', ansible_config)
    base_cfg = ansible_config('github_user_1')

    ga = GithubAdminClient()
    suffix = ''.join([random.choice(string.ascii_lowercase) for x in range(0, 5)])
    user_a = ga.create_user(login='0xEEE-32i-' + suffix)
    user_a['username'] = user_a['login']
    user_a['token'] = None
    user_a['url'] = base_cfg.get('url')
    user_a['auth_url'] = base_cfg.get('auth_url')
    user_a['github_url'] = base_cfg.get('github_url')
    user_a['github_api_url'] = base_cfg.get('github_api_url')
    l_ns_name = user_a['username']

    # login once to confirm v3 namespace creation
    with SocialGithubClient(config=user_a) as client:
        a_resp = client.get('_ui/v1/me/')
        a_ds = a_resp.json()
        assert a_ds['username'] == user_a['username']

        ns_resp = client.get('_ui/v1/my-namespaces/')
        ns_ds = ns_resp.json()
        assert ns_ds['meta']['count'] == 1, ns_ds

        original_namespace = ns_ds['data'][0]['name']

        # verify the new legacy namespace has right owner ...
        l_ns_name = user_a['username']
        l_resp = client.get(f'v1/namespaces/?name={l_ns_name}')
        l_ns_ds = l_resp.json()
        assert l_ns_ds['count'] == 1, l_ns_ds
        assert l_ns_ds['results'][0]['name'] == l_ns_name, l_ns_ds
        assert l_ns_ds['results'][0]['summary_fields']['owners'][0]['username'] == \
            user_a['username'], l_ns_ds

        # verify the legacy provider namespace is the v3 namespace
        provider_namespaces = l_ns_ds['results'][0]['summary_fields']['provider_namespaces']
        assert len(provider_namespaces) == 1
        provider_namespace = provider_namespaces[0]
        assert provider_namespace['name'].startswith('gh_')

    # make a new login
    new_login = user_a['login'] + '-changed'

    # change the user's login and try again
    user_b = ga.modify_user(uid=user_a['id'], change=('login', new_login))
    user_b['username'] = user_b['login']
    user_b['token'] = None
    user_b['url'] = base_cfg.get('url')
    user_b['auth_url'] = base_cfg.get('auth_url')
    user_b['github_url'] = base_cfg.get('github_url')
    user_b['github_api_url'] = base_cfg.get('github_api_url')

    # current_users = ga.list_users()

    with SocialGithubClient(config=user_b) as client:
        b_resp = client.get('_ui/v1/me/')
        b_ds = b_resp.json()

        # the UID should have stayed the same
        assert b_ds['id'] == a_ds['id']

        # the backend should have changed the username
        assert b_ds['username'] == user_b['username']

        # now check the namespaces again ...
        ns_resp2 = client.get('_ui/v1/my-namespaces/')
        ns_ds2 = ns_resp2.json()

        # there should be 2 ...
        assert ns_ds2['meta']['count'] == 2, ns_ds2

        # one of them should be the one created with the previous username
        ns_names = [x['name'] for x in ns_ds2['data']]
        assert original_namespace in ns_names, ns_names

        # verify the previous legacy namespace has right owner ...
        l_resp = client.get(f'v1/namespaces/?name={l_ns_name}')
        l_ns_ds = l_resp.json()
        assert l_ns_ds['count'] == 1, l_ns_ds
        assert l_ns_ds['results'][0]['name'] == l_ns_name, l_ns_ds
        assert l_ns_ds['results'][0]['summary_fields']['owners'][0]['username'] == \
            user_b['username'], l_ns_ds

        # verify the new legacy namespace has right owner ...
        new_l_ns = user_b['username']
        new_l_resp = client.get(f'v1/namespaces/?name={new_l_ns}')
        new_l_ns_ds = new_l_resp.json()
        assert new_l_ns_ds['count'] == 1, new_l_ns_ds
        assert new_l_ns_ds['results'][0]['name'] == new_l_ns, new_l_ns_ds
        assert new_l_ns_ds['results'][0]['summary_fields']['owners'][0]['username'] == \
            user_b['username'], new_l_ns_ds

        # verify the new legacy ns has the new provider ns
        provider_namespaces = new_l_ns_ds['results'][0]['summary_fields']['provider_namespaces']
        assert len(provider_namespaces) == 1
        provider_namespace = provider_namespaces[0]
        assert provider_namespace['name'].startswith('gh_')

    with SocialGithubClient(config=user_b) as client:

        pass

        # the new login should be able to find all of their legacy namespaces
        # import epdb; epdb.st()

        # the new login should be able to import to BOTH legacy namespaces

        # the new login should be able to find all of their v3 namespaces

        # the new login should be able to upload to BOTH v3 namespaces

    # TODO ... what happens with the other owners of a v1 namespace when
    #   the original owner changes their login?
    # TODO ... what happens with the other owners of a v3 namespace when
    #   the original owner changes their login?


@pytest.mark.deployment_community
def test_social_user_with_reclaimed_login(ansible_config):

    '''
    [jtanner@jtw530 galaxy_user_analaysis]$ head -n1 data/user_errors.csv
    galaxy_uid,galaxy_username,github_id,github_login,actual_github_id,actual_github_login
    [jtanner@jtw530 galaxy_user_analaysis]$ grep sean-m-sullivan data/user_errors.csv
    33901,Wilk42,30054029,sean-m-sullivan,30054029,sean-m-sullivan
    '''

    # a user logged into galaxy once with login "foo"
    # the user then changed their name in github to "bar"
    # the user then logged back into galaxy ...
    #
    #   1) social auth updates it's own data based on the github userid
    #   2) galaxy's user still has the old login but is linked to the same social account

    # What happens when someone claims the old username ..?
    #
    #   Once they login to galaxy they will get the "foo" login as their username?
    #   the "foo" namespace will not belong to them
    #   the "bar" namespace will not belong to them
    #   do they own -any- namespaces?

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    ga = GithubAdminClient()
    ga.delete_user(login='Wilk42')
    ga.delete_user(login='sean-m-sullivan')
    cleanup_social_user('Wilk42', ansible_config)
    cleanup_social_user('sean-m-sullivan', ansible_config)
    cleanup_social_user('sean_m_sullivan', ansible_config)
    cleanup_social_user('sean-m-sullivan@redhat.com', ansible_config)

    default_cfg = extract_default_config(ansible_config)

    nsmap = {}
    next_url = '/api/v3/namespaces/'
    while next_url:
        resp = admin_client(next_url)
        nsmap.update(dict((x['name'], x) for x in resp['data']))
        next_url = resp['links']['next']
    for nsname, nsdata in nsmap.items():
        if not nsname.lower().startswith('sean_m') and not nsname.lower().startswith('wilk42'):
            continue
        cleanup_social_user(nsname, ansible_config)
        cleanup_namespace(nsname, api_client=admin_client)

    old_login = 'Wilk42'
    email = 'sean-m-sullivan@redhat.com'
    user_a = ga.create_user(login=old_login, email=email)
    user_a.update(default_cfg)
    user_a['username'] = old_login

    # login once to make user
    with SocialGithubClient(config=user_a) as client:
        a_resp = client.get('_ui/v1/me/')
        ns_resp = client.get('_ui/v1/my-namespaces/')
        ns_ds = ns_resp.json()
        namespace_names_a = [x['name'] for x in ns_ds['data']]

    # make a sean_m_sullivan namespace owned by the old login ... ?

    # make a new login
    new_login = 'sean-m-sullivan'

    # change the user's login and try again
    user_b = ga.modify_user(uid=user_a['id'], change=('login', new_login))
    user_b.update(default_cfg)
    user_b['username'] = new_login

    # sean-m-sullivan never logs in again ...
    '''
    with SocialGithubClient(config=user_b) as client:
        b_resp = client.get('_ui/v1/me/')
    '''

    # Let some new person claim the old login ...
    user_c = ga.create_user(login=old_login, email='shadyperson@haxx.net')
    user_c.update(default_cfg)
    user_c['username'] = old_login

    with SocialGithubClient(config=user_c) as client:
        c_resp = client.get('_ui/v1/me/')
        ns_resp_c = client.get('_ui/v1/my-namespaces/')
        ns_ds_c = ns_resp_c.json()
        namespace_names_c = [x['name'] for x in ns_ds_c['data']]

    # user_a and user_c should have different galaxy uids
    assert a_resp.json()['id'] != c_resp.json()['id']

    # user_c should have the old login
    assert c_resp.json()['username'] == old_login

    # user_c should not own the namespaces of user_a
    for ns in namespace_names_a:
        assert ns not in namespace_names_c

    # now sean logs in with his new login ...
    with SocialGithubClient(config=user_b) as client:
        b_resp = client.get('_ui/v1/me/')
        ns_resp_b = client.get('_ui/v1/my-namespaces/')
        ns_ds_b = ns_resp_b.json()
        namespace_names_b = [x['name'] for x in ns_ds_b['data']]

    # his ID should be the same
    assert b_resp.json()['id'] == a_resp.json()['id']

    # his username should be the new login
    assert b_resp.json()['username'] == new_login

    # he should own his old namespace AND a transformed one from his new login
    assert namespace_names_b == ['wilk42', 'sean_m_sullivan']


@pytest.mark.deployment_community
def test_social_user_sync_with_changed_login(ansible_config):

    # https://galaxy.ansible.com/api/v1/users/?username=Wilk42
    #   github_id:30054029

    # https://galaxy.ansible.com/api/v1/roles/21352/
    #   Wilk42/kerb_ldap_setup
    #   Wilk42.kerb_ldap_setup
    # https://galaxy.ansible.com/api/v1/namespaces/1838/
    #   owner: 33901:Wilk42

    ga = GithubAdminClient()
    ga.delete_user(login='Wilk42')
    ga.delete_user(login='sean-m-sullivan')
    cleanup_social_user('Wilk42', ansible_config)
    cleanup_social_user('wilk42', ansible_config)
    cleanup_social_user('wilk420', ansible_config)
    cleanup_social_user('Wilk420', ansible_config)
    cleanup_social_user('wilk421', ansible_config)
    cleanup_social_user('Wilk421', ansible_config)
    cleanup_social_user('sean-m-sullivan', ansible_config)
    cleanup_social_user('sean-m-sullivan@redhat.com', ansible_config)
    cleanup_social_user('30054029@GALAXY.GITHUB.UNVERIFIED.COM', ansible_config)

    default_cfg = extract_default_config(ansible_config)

    # sync the wilk42 v1 namespace ...
    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    # find all the wilk* namespaces and clean them up ...
    resp = admin_client('/api/v3/namespaces/')
    nsmap = dict((x['name'], x) for x in resp['data'])
    for nsname, nsdata in nsmap.items():
        if not nsname.startswith('wilk'):
            continue
        cleanup_namespace(nsname, api_client=admin_client)

    # v1 sync the user's roles and namespace ...
    pargs = json.dumps({"github_user": 'Wilk42', "limit": 1}).encode('utf-8')
    resp = admin_client('/api/v1/sync/', method='POST', args=pargs)
    wait_for_v1_task(resp=resp, api_client=admin_client)

    # should have same roles
    roles_resp = admin_client.request('/api/v1/roles/?namespace=Wilk42')
    assert roles_resp['count'] >= 1
    roles = roles_resp['results']
    v1_namespace_summary = roles[0]['summary_fields']['namespace']
    v1_namespace_id = v1_namespace_summary['id']
    v1_namespace_name = v1_namespace_summary['name']

    assert v1_namespace_name == 'Wilk42'

    # should have a v1 namespace with Wilk42 as the owner?
    ns1_owners_resp = admin_client.request(f'/api/v1/namespaces/{v1_namespace_id}/owners/')
    assert ns1_owners_resp
    ns1_owners_ids = [x['id'] for x in ns1_owners_resp]
    ns1_owners_usernames = [x['username'] for x in ns1_owners_resp]
    assert 'Wilk42' in ns1_owners_usernames

    # should have a v3 namespace
    ns1_resp = admin_client.request(f'/api/v1/namespaces/{v1_namespace_id}/')
    provider_namespaces = ns1_resp['summary_fields']['provider_namespaces']
    assert provider_namespaces
    provider_namespace = provider_namespaces[0]
    # v3_namespace_id = provider_namespace['id']
    v3_namespace_name = provider_namespace['name']
    assert v3_namespace_name == 'wilk42'

    # now some new person who took Wilk42 logs in ...
    hacker = ga.create_user(login='Wilk42', email='1337h@xx.net')
    hacker['username'] = hacker['login']
    hacker.update(default_cfg)
    with SocialGithubClient(config=hacker) as client:
        hacker_me_resp = client.get('_ui/v1/me/')
        hacker_me_ds = hacker_me_resp.json()

        # check the hacker's namespaces ...
        hacker_ns_resp = client.get('_ui/v1/my-namespaces/')
        hacker_ns_ds = hacker_ns_resp.json()
        hacker_ns_names = [x['name'] for x in hacker_ns_ds['data']]

    # enure the hacker has a new uid
    assert hacker_me_ds['id'] != ns1_owners_ids[0]

    # ensure the hacker owns only some newly created v3 namespace
    assert hacker_ns_names == ['wilk420']

    # now sean-m-sullivan who used to be Wilk42 logs in ...
    sean = ga.create_user(login='sean-m-sullivan', uid=30054029, email='sean-m-sullivan@redhat.com')
    sean['username'] = sean['login']
    sean.update(default_cfg)

    with SocialGithubClient(config=sean) as client:
        me_resp = client.get('_ui/v1/me/')
        me_ds = me_resp.json()

        # now check the namespaces again ...
        ns_resp = client.get('_ui/v1/my-namespaces/')
        ns_ds = ns_resp.json()
        sean_ns_names = [x['name'] for x in ns_ds['data']]

    # he should have the appropriate username
    assert me_ds['username'] == 'sean-m-sullivan'
    # he should own the old and a new v3 namespaces
    assert sean_ns_names == ['wilk42', 'sean_m_sullivan']
    # his uid should have remained the same
    assert me_ds['id'] == ns1_owners_ids[0]

    # he should own the original v1 namespaces
    ns1_owners_resp_after = admin_client.request(f'/api/v1/namespaces/{v1_namespace_id}/owners/')
    ns1_owner_names_after = [x['username'] for x in ns1_owners_resp_after]
    assert ns1_owner_names_after == ['sean-m-sullivan']

    # he should own a new v1 namespace too ...
    ns_resp = admin_client('/api/v1/namespaces/?owner=sean-m-sullivan')
    assert ns_resp['count'] == 2
    v1_ns_names = [x['name'] for x in ns_resp['results']]
    assert v1_ns_names == ['Wilk42', 'sean-m-sullivan']

    # what happens when someone installs Wilk42's roles ...
    #   galaxy.ansible.com shows the role as wilk42/kerb_ldap_setup
    #   installing with wilk42.kerb_ldap_setup and Wilk42.kerb_ldap_setup should both work
    #   the backend finds the role with owner__username=wilk42 AND owner__username=Wilk42
    #   the role data has github_repo=Wilk42 which is what the client uses
    #    github then has a redirect from Wilk42/kerb_ldap_setup to sean-m-sullivan/kerb_ldap_setup
    #   i believe that redirect no longer works after someone claims Wilk42

    # core code ...
    #   url = _urljoin(self.api_server, self.available_api_versions['v1'], "roles",
    #                   "?owner__username=%s&name=%s" % (user_name, role_name))
    # 	archive_url = 'https://github.com/%s/%s/archive/%s.tar.gz' %
    #       (role_data["github_user"], role_data["github_repo"], self.version)

    for role in roles:
        for owner_username in ['Wilk42', 'wilk42']:
            role_name = role['name']
            role_data = admin_client.request(
                f'/api/v1/roles/?owner__username={owner_username}&name={role_name}'
            )
            assert role_data['count'] == 1
            assert role_data['results'][0]['id'] == role['id']
            assert role_data['results'][0]['github_user'] == 'Wilk42'
            assert role_data['results'][0]['github_repo'] == role['github_repo']
            assert role_data['results'][0]['name'] == role['name']


@pytest.mark.skip(reason='this should be unit tested')
@pytest.mark.deployment_community
def test_rbac_utils_get_owned_v3_namespaces(ansible_config):
    pass


@pytest.mark.skip(reason='this should be unit tested')
@pytest.mark.deployment_community
def test_community_tools_urls(ansible_config):
    pass


@pytest.mark.deployment_community
def test_social_auth_no_duplicated_namespaces(ansible_config):

    # https://issues.redhat.com/browse/AAH-2729

    ga = GithubAdminClient()
    ga.delete_user(login='Wilk42')
    ga.delete_user(login='sean-m-sullivan')
    cleanup_social_user('sean-m-sullivan', ansible_config)
    cleanup_social_user('Wilk42', ansible_config)
    cleanup_social_user('wilk42', ansible_config)
    cleanup_social_user('sean-m-sullivan@findme.net', ansible_config)
    cleanup_social_user('30054029@GALAXY.GITHUB.UNVERIFIED.COM', ansible_config)

    default_cfg = extract_default_config(ansible_config)

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    # find all the sean_m* namespaces and clean them up ...
    nsmap = {}
    next_url = '/api/v3/namespaces/'
    while next_url:
        resp = admin_client(next_url)
        nsmap.update(dict((x['name'], x) for x in resp['data']))
        next_url = resp['links']['next']
    for nsname, nsdata in nsmap.items():
        if not nsname.startswith('sean_m') and not nsname.startswith('wilk42'):
            continue
        cleanup_social_user(nsname, ansible_config)
        cleanup_namespace(nsname, api_client=admin_client)

    # make sean_m_sullivan namespace with no owners?
    api_prefix = admin_client.config.get("api_prefix").rstrip("/")
    payload = {'name': 'sean_m_sullivan', 'groups': []}
    resp = admin_client(f'{api_prefix}/v3/namespaces/', args=payload, method='POST')

    # make sean-m-sullivan on github
    ga.delete_user(login='sean-m-sullivan')
    sean = ga.create_user(login='sean-m-sullivan', email='sean@findme.net', uid=30054029)
    sean['username'] = sean['login']
    sean.update(default_cfg)

    # login 10 times ...
    for x in range(0, 10):
        with SocialGithubClient(config=sean) as client:
            client.get('_ui/v1/me/')

    # check to make sure only the one ns was created ...
    nsmap = {}
    next_url = '/api/v3/namespaces/'
    while next_url:
        resp = admin_client(next_url)
        nsmap.update(dict((x['name'], x) for x in resp['data']))
        next_url = resp['links']['next']
    sean_namespaces = sorted([x for x in nsmap.keys() if x.startswith('sean_m')])
    assert sean_namespaces == ['sean_m_sullivan', 'sean_m_sullivan0']


@pytest.mark.skip(reason='this should be unit tested')
@pytest.mark.deployment_community
def test_community_social_v3_namespace_sorting(ansible_config):
    # https://issues.redhat.com/browse/AAH-2729
    # social auth code was trying to sort namespaces ...
    pass


@pytest.mark.deployment_community
def test_social_auth_access_api_ui_v1_users(ansible_config):
    # https://issues.redhat.com/browse/AAH-2781

    username = "foo1234"
    default_cfg = extract_default_config(ansible_config)

    ga = GithubAdminClient()
    ga.delete_user(login=username)

    user_c = ga.create_user(login=username, email="foo1234@gmail.com")
    user_c.update(default_cfg)
    user_c['username'] = username

    with SocialGithubClient(config=user_c) as client:
        users_resp = client.get('_ui/v1/users/')
        assert users_resp.status_code == 200

        # try to fetch each user ..
        for udata in users_resp.json()['data']:
            uid = udata['id']
            user_resp = client.get(f'_ui/v1/users/{uid}/')
            assert user_resp.status_code == 200
