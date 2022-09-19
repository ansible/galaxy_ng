#!/usr/bin/env python3

import random

import pytest
from ansible.galaxy.api import GalaxyError
from jsonschema import validate as validate_json

from ..constants import DEFAULT_DISTROS
from ..schemas import (
    schema_collection_import,
    schema_collection_import_detail,
    schema_collectionversion,
    schema_collectionversion_metadata,
    schema_distro,
    schema_distro_repository,
    schema_ee_registry,
    schema_ee_namespace_detail,
    schema_featureflags,
    schema_group,
    schema_me,
    schema_namespace_detail,
    schema_objectlist,
    schema_remote,
    schema_settings,
    schema_task,
    schema_user,
)
from ..utils import UIClient, generate_unused_namespace, get_client, wait_for_task_ui_client
from .rbac_actions.utils import podman_push

from orionutils.generator import randstr

REGEX_403 = r"HTTP Code: 403"


# /api/automation-hub/_ui/v1/auth/login/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_login(ansible_config):

    cfg = ansible_config("basic_user")

    # an authenticated session has a csrftoken and a sessionid
    with UIClient(config=cfg) as uclient:
        assert uclient.cookies['csrftoken'] is not None
        assert uclient.cookies['sessionid'] is not None


# /api/automation-hub/_ui/v1/auth/logout/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_logout(ansible_config):

    cfg = ansible_config("basic_user")
    uclient = UIClient(config=cfg)

    # check the auth first
    uclient.login()
    assert uclient.cookies['csrftoken'] is not None
    assert uclient.cookies['sessionid'] is not None

    # logout should clear the sessionid but not the csrftoken
    uclient.logout(expected_code=204)
    assert uclient.cookies['csrftoken'] is not None
    assert 'sessionid' not in uclient.cookies


# /api/automation-hub/_ui/v1/collection-versions/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_collection_versions(ansible_config, uncertifiedv2):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:
        resp = uclient.get('_ui/v1/collection-versions/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        assert len(ds['data']) >= 1

        for cv in ds['data']:
            validate_json(instance=cv, schema=schema_collectionversion)
            validate_json(instance=cv['metadata'], schema=schema_collectionversion_metadata)

            # try to get the direct url for this version ...
            cv_url = f"_ui/v1/collection-versions/{cv['namespace']}/{cv['name']}/{cv['version']}/"
            cv_resp = uclient.get(cv_url)
            assert cv_resp.status_code == 200

            ds = cv_resp.json()
            validate_json(instance=ds, schema=schema_collectionversion)
            validate_json(instance=ds['metadata'], schema=schema_collectionversion_metadata)


# /api/automation-hub/_ui/v1/collection-versions/{version}/
# ^ tested by previous function


# /api/automation-hub/_ui/v1/collection_signing/
# /api/automation-hub/_ui/v1/collection_signing/{path}/
# /api/automation-hub/_ui/v1/collection_signing/{path}/{namespace}/
# /api/automation-hub/_ui/v1/collection_signing/{path}/{namespace}/{collection}/
# /api/automation-hub/_ui/v1/collection_signing/{path}/{namespace}/{collection}/{version}/
# /api/automation-hub/_ui/v1/controllers/


# /api/automation-hub/_ui/v1/distributions/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_distributions(ansible_config):
    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:
        resp = uclient.get('_ui/v1/distributions/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        for distro in ds['data']:
            validate_json(instance=distro, schema=schema_distro)
            validate_json(instance=distro['repository'], schema=schema_distro_repository)

        # make sure all default distros are in the list ...
        distro_tuples = [(x['name'], x['base_path']) for x in ds['data']]
        for k, v in DEFAULT_DISTROS.items():
            key = (k, v['basepath'])
            assert key in distro_tuples


# /api/automation-hub/_ui/v1/distributions/{pulp_id}/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_distributions_by_id(ansible_config):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/distributions/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        for distro in ds['data']:
            validate_json(instance=distro, schema=schema_distro)

        # check the endpoint for each distro by pulp id ...
        distro_ids = [x['pulp_id'] for x in ds['data']]
        for distro_id in distro_ids:
            resp = uclient.get(f'_ui/v1/distributions/{distro_id}')
            assert resp.status_code == 200
            _ds = resp.json()
            validate_json(instance=_ds, schema=schema_distro)
            validate_json(instance=_ds['repository'], schema=schema_distro_repository)
            assert _ds['pulp_id'] == distro_id


# /api/automation-hub/_ui/v1/execution-environments/registries/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_execution_environments_registries(ansible_config):

    cfg = ansible_config('ee_admin')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/execution-environments/registries/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        # try to create one
        suffix = random.choice(range(0, 1000))
        rname = f'redhat.io.{suffix}'
        payload = {
            'name': rname,
            'url': 'https://registry.redhat.io',
        }
        resp = uclient.post('_ui/v1/execution-environments/registries/', payload=payload)
        assert resp.status_code == 201
        rds = resp.json()
        validate_json(instance=rds, schema=schema_ee_registry)

        # try to get it by pulp_id
        resp = uclient.get(f"_ui/v1/execution-environments/registries/{rds['pk']}/")
        assert resp.status_code == 200
        rds = resp.json()
        validate_json(instance=rds, schema=schema_ee_registry)

        # sync it
        resp = uclient.post(
            f"_ui/v1/execution-environments/registries/{rds['pk']}/sync/",
            payload={}
        )
        assert resp.status_code == 202
        task = resp.json()
        validate_json(instance=task, schema=schema_task)

        # wait for sync to finish
        wait_for_task_ui_client(uclient, task)

        # index it
        resp = uclient.post(
            f"_ui/v1/execution-environments/registries/{rds['pk']}/index/",
            payload={}
        )
        assert resp.status_code == 202
        task = resp.json()
        validate_json(instance=task, schema=schema_task)

        # wait for index to finish
        wait_for_task_ui_client(uclient, task)

        # delete the registry
        resp = uclient.delete(f"_ui/v1/execution-environments/registries/{rds['pk']}/")
        assert resp.status_code == 204

        # make sure it's gone
        resp = uclient.get(f"_ui/v1/execution-environments/registries/{rds['pk']}/")
        assert resp.status_code == 404


# /api/automation-hub/_ui/v1/execution-environments/registries/{pulp_id}/
# ^ tested by previous function


# /api/automation-hub/_ui/v1/execution-environments/registries/{id}/index/
# ^ tested by previous function


# /api/automation-hub/_ui/v1/execution-environments/registries/{id}/sync/
# ^ tested by previous function


# /api/automation-hub/_ui/v1/execution-environments/remotes/
# /api/automation-hub/_ui/v1/execution-environments/remotes/{pulp_id}/
# /api/automation-hub/_ui/v1/execution-environments/repositories/{base_path}/_content/history/
# /api/automation-hub/_ui/v1/execution-environments/repositories/{base_path}/_content/images/
# /api/automation-hub/_ui/v1/execution-environments/repositories/{base_path}/_content/images/{manifest_ref}/
# /api/automation-hub/_ui/v1/execution-environments/repositories/{base_path}/_content/readme/
# /api/automation-hub/_ui/v1/execution-environments/repositories/{base_path}/_content/sync/
# /api/automation-hub/_ui/v1/execution-environments/repositories/{base_path}/_content/tags/

# /api/automation-hub/_ui/v1/execution-environments/repositories/
# /api/automation-hub/_ui/v1/execution-environments/repositories/{base_path}/
# /api/automation-hub/_ui/v1/execution-environments/namespaces/
# /api/automation-hub/_ui/v1/execution-environments/namespaces/{name}/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_execution_environments_repositories(ansible_config):
    cfg = ansible_config('ee_admin')
    new_namespace = f'ns_{randstr()}'
    new_repository = f'repo_{randstr()}'
    new_name = f'{new_namespace}/{new_repository}'

    podman_push(cfg['username'], cfg['password'], new_name)

    with UIClient(config=cfg) as uclient:

        # get the ee repositories view
        repository_resp = uclient.get('_ui/v1/execution-environments/repositories/')
        assert repository_resp.status_code == 200

        # assert the correct response serializer
        repository_ds = repository_resp.json()
        validate_json(instance=repository_ds, schema=schema_objectlist)

        # validate new repository was created
        repository_names = [x['name'] for x in repository_ds['data']]
        assert new_name in repository_names

        # get the namespaces list
        namespace_resp = uclient.get('_ui/v1/execution-environments/namespaces/')
        assert namespace_resp.status_code == 200

        # assert correct response serializer
        namespace_ds = namespace_resp.json()
        validate_json(instance=namespace_ds, schema=schema_objectlist)

        # assert new namespace was created
        assert new_namespace in [x['name'] for x in namespace_ds['data']]

        ns_detail_resp = uclient.get(f'_ui/v1/execution-environments/namespaces/{new_namespace}')
        assert ns_detail_resp.status_code == 200

        # assert correct response serializer
        ns_detail_ds = ns_detail_resp.json()
        validate_json(instance=ns_detail_ds, schema=schema_ee_namespace_detail)

        # assert new namespace was created
        assert new_namespace == ns_detail_ds['name']
        assert cfg['username'] in ns_detail_ds['owners']

        # delete the respository
        delete_repository_resp = uclient.delete(
            f'_ui/v1/execution-environments/repositories/{new_name}/'
        )
        assert delete_repository_resp.status_code == 202
        task = delete_repository_resp.json()
        wait_for_task_ui_client(uclient, task)

        # get the repositories list again
        repository_resp = uclient.get('_ui/v1/execution-environments/repositories/')
        assert repository_resp.status_code == 200

        # assert the new repository has been deleted
        repository_ds = repository_resp.json()
        repository_names = [x['name'] for x in repository_ds['data']]

        assert new_name not in repository_names


# /api/automation-hub/_ui/v1/feature-flags/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_feature_flags(ansible_config):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/feature-flags/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_featureflags)


# /api/automation-hub/_ui/v1/groups/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_groups(ansible_config):

    cfg = ansible_config('partner_engineer')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/groups/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        for grp in ds['data']:
            validate_json(instance=grp, schema=schema_group)

        # try to make a group
        suffix = random.choice(range(0, 1000))
        payload = {'name': f'foobar{suffix}'}
        resp = uclient.post('_ui/v1/groups/', payload=payload)
        assert resp.status_code == 201

        ds = resp.json()
        validate_json(instance=ds, schema=schema_group)
        assert ds['name'] == payload['name']
        assert ds['pulp_href'].endswith(f"/{ds['id']}/")


# /api/automation-hub/_ui/v1/groups/{group_pk}/model-permissions/
# /api/automation-hub/_ui/v1/groups/{group_pk}/model-permissions/{id}/


# /api/automation-hub/_ui/v1/groups/{group_pk}/users/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_groups_users(ansible_config):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:
        resp = uclient.get('_ui/v1/groups/')
        assert resp.status_code == 200
        groups_ds = resp.json()
        validate_json(instance=groups_ds, schema=schema_objectlist)

        # get the primary key for PE
        pe_id = None
        for x in groups_ds['data']:
            if x['name'] == 'system:partner-engineers':
                pe_id = x['id']
                break
        assert pe_id is not None

        # validate username="jdoe" is in the group's userlist
        resp = uclient.get(f'_ui/v1/groups/{pe_id}/users/')
        assert resp.status_code == 200
        users_ds = resp.json()
        validate_json(instance=users_ds, schema=schema_objectlist)
        assert "jdoe" in [x["username"] for x in users_ds["data"]]


# /api/automation-hub/_ui/v1/groups/{group_pk}/users/{id}/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_groups_users_add_delete(ansible_config):

    cfg = ansible_config('partner_engineer')
    with UIClient(config=cfg) as uclient:

        suffix = random.choice(range(0, 1000))
        group_name = f'group{suffix}'
        user_name = f'user{suffix}'

        # make the group
        resp = uclient.post('_ui/v1/groups/', payload={'name': group_name})
        assert resp.status_code == 201
        group_ds = resp.json()
        validate_json(instance=group_ds, schema=schema_group)
        group_id = group_ds['id']

        # make the user
        resp = uclient.post(
            '_ui/v1/users/',
            payload={
                'username': user_name,
                'first_name': 'foo',
                'last_name': 'bar',
                'email': 'foo@barz.com',
                'groups': [group_ds],
                'password': 'abcdefghijklmnopqrstuvwxyz1234567890!@#$%^&*()-+',
                'is_superuser': False
            }
        )
        assert resp.status_code == 201
        user_ds = resp.json()
        validate_json(instance=user_ds, schema=schema_user)

        # validate the new user is in the group's userlist
        resp = uclient.get(f'_ui/v1/groups/{group_id}/users/')
        assert resp.status_code == 200
        users_ds = resp.json()
        validate_json(instance=users_ds, schema=schema_objectlist)
        assert user_name in [x['username'] for x in users_ds['data']]

        # remove the user from the group
        user_id = user_ds['id']
        resp = uclient.delete(f'_ui/v1/groups/{group_id}/users/{user_id}/')
        assert resp.status_code == 204
        assert resp.text == ''

        # validate the new user is NOT in the group's userlist
        resp = uclient.get(f'_ui/v1/groups/{group_id}/users/')
        assert resp.status_code == 200
        users_ds = resp.json()
        validate_json(instance=users_ds, schema=schema_objectlist)
        assert user_name not in [x['username'] for x in users_ds['data']]


# /api/automation-hub/_ui/v1/groups/{id}/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_groups_by_id(ansible_config):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/groups/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        for grp in ds['data']:
            gid = grp['id']
            gresp = uclient.get(f'_ui/v1/groups/{gid}/')
            assert gresp.status_code == 200
            ds = gresp.json()
            validate_json(instance=ds, schema=schema_group)
            assert ds['id'] == gid


# /api/automation-hub/_ui/v1/imports/collections/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_imports_collections(ansible_config):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/imports/collections/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        for job in ds['data']:
            validate_json(instance=job, schema=schema_collection_import)
            task_id = job['id']
            jurl = f'_ui/v1/imports/collections/{task_id}/'
            jresp = uclient.get(jurl)
            assert jresp.status_code == 200
            jds = jresp.json()
            validate_json(instance=jds, schema=schema_collection_import_detail)


# /api/automation-hub/_ui/v1/imports/collections/{task_id}/
# ^ tested by the previous function


# /api/automation-hub/_ui/v1/landing-page/
# ^ tested in tests/integration/api/test_landing_page.py


# /api/automation-hub/_ui/v1/me/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_me(ansible_config):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/me')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_me)

        assert not ds['is_anonymous']
        assert ds['username'] == cfg.get('username')
        assert ds['auth_provider'] == ['django']


# /api/automation-hub/_ui/v1/my-distributions/
# /api/automation-hub/_ui/v1/my-distributions/{pulp_id}/


# /api/automation-hub/_ui/v1/my-namespaces/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_my_namespaces(ansible_config):
    config = ansible_config("partner_engineer")
    api_client = get_client(config, request_token=True, require_auth=True)
    new_namespace = generate_unused_namespace(api_client=api_client, api_version='_ui/v1')

    cfg = ansible_config('partner_engineer')
    with UIClient(config=cfg) as uclient:
        # get user
        resp = uclient.get('_ui/v1/me/')
        ds = resp.json()

        # create ns with group
        # TODO: Add user's roles to the me endpoint
        payload = {
            'name': new_namespace,
            'groups': [{
                'id': ds['groups'][0]['id'],
                'name': ds['groups'][0]['name'],
                'object_roles': ["galaxy.collection_admin"],
            }]
        }
        presp = uclient.post('_ui/v1/my-namespaces/', payload=payload)
        assert presp.status_code == 201

        # get the my-namespaces view
        resp = uclient.get('_ui/v1/my-namespaces/')
        assert resp.status_code == 200

        # assert the correct response serializer
        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        # get all the namespaces in the view
        namespace_names = uclient.get_paginated('_ui/v1/my-namespaces/')
        namespace_names = [x['name'] for x in namespace_names]

        # validate the new one shows up
        for expected_ns_name in ['autohubtest2', 'autohubtest3', 'signing', new_namespace]:
            assert expected_ns_name in namespace_names

        # delete
        resp = uclient.delete(f'_ui/v1/my-namespaces/{new_namespace}')
        assert resp.status_code == 204

        # get the response
        resp = uclient.get('_ui/v1/my-namespaces/')
        assert resp.status_code == 200

        # confirm deletion
        namespace_names = uclient.get_paginated('_ui/v1/my-namespaces/')
        namespace_names = [x['name'] for x in namespace_names]
        assert new_namespace not in namespace_names


# /api/automation-hub/_ui/v1/my-namespaces/{name}/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_my_namespaces_name(ansible_config):
    cfg = ansible_config('partner_engineer')
    with UIClient(config=cfg) as uclient:
        # get the response
        resp = uclient.get('_ui/v1/my-namespaces/autohubtest2/')
        assert resp.status_code == 200
        validate_json(instance=resp.json(), schema=schema_namespace_detail)


# /api/automation-hub/_ui/v1/my-synclists/
# /api/automation-hub/_ui/v1/my-synclists/{id}/
# /api/automation-hub/_ui/v1/my-synclists/{id}/curate/


# /api/automation-hub/_ui/v1/namespaces/
# ^ tested in tests/integration/api/test_namespace_management.py


# /api/automation-hub/_ui/v1/namespaces/{name}/
# ^ tested in tests/integration/api/test_namespace_management.py


# /api/automation-hub/_ui/v1/remotes/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_remotes(ansible_config):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/remotes/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        for remote in ds['data']:
            validate_json(instance=remote, schema=schema_remote)

        remote_names = [x['name'] for x in ds['data']]
        assert 'community' in remote_names
        assert 'rh-certified' in remote_names


# /api/automation-hub/_ui/v1/remotes/{pulp_id}/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_remotes_by_id(ansible_config):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/remotes/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        for remote in ds['data']:
            validate_json(instance=remote, schema=schema_remote)

        # FIXME - there is no suitable pulp_id for a remote?
        pulp_ids = [x['pk'] for x in ds['data']]
        for pulp_id in pulp_ids:
            resp = uclient.get('_ui/v1/remotes/{pulp_id}/')
            assert resp.status_code == 404


# /api/automation-hub/_ui/v1/repo/{distro_base_path}/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_repo_distro_by_basepath(ansible_config):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:

        # get each repo by basepath? or is it get a distro by basepath?
        for k, v in DEFAULT_DISTROS.items():
            bp = v['basepath']
            resp = uclient.get(f'_ui/v1/repo/{bp}')
            ds = resp.json()
            validate_json(instance=ds, schema=schema_objectlist)


# /api/automation-hub/_ui/v1/repo/{distro_base_path}/{namespace}/{name}/
# ^ FIXME - need some examples


# /api/automation-hub/_ui/v1/settings/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_settings(ansible_config):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/settings/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_settings)

        # FIXME - password length and token expiration are None?
        assert ds['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS'] is False
        assert ds['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD'] is False
        assert ds['GALAXY_REQUIRE_CONTENT_APPROVAL'] is True


# /api/automation-hub/_ui/v1/synclists/
# /api/automation-hub/_ui/v1/synclists/{id}/


# /api/automation-hub/_ui/v1/tags/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_tags(ansible_config):

    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/tags/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        # FIXME - ui tags api does not support POST?


# /api/automation-hub/_ui/v1/users/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_users(ansible_config):

    cfg = ansible_config('partner_engineer')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/users/')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_objectlist)

        assert len(ds['data']) >= 1
        for user in ds['data']:
            validate_json(instance=user, schema=schema_user)

        # try creating a user
        suffix = random.choice(range(0, 9999))
        payload = {
            'username': f'foobar{suffix}',
            'first_name': 'foobar',
            'last_name': f'{suffix}'
        }
        resp = uclient.post('_ui/v1/users/', payload=payload)
        assert resp.status_code == 201

        ds = resp.json()
        validate_json(instance=ds, schema=schema_user)

        # should NOT be superuser by default
        assert not ds['is_superuser']

        assert ds['username'] == payload['username']
        assert ds['first_name'] == payload['first_name']
        assert ds['last_name'] == payload['last_name']


# /api/automation-hub/_ui/v1/users/{id}/
@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_users_by_id(ansible_config):

    cfg = ansible_config('partner_engineer')
    with UIClient(config=cfg) as uclient:

        # get the response
        resp = uclient.get('_ui/v1/users/2')
        assert resp.status_code == 200

        ds = resp.json()
        validate_json(instance=ds, schema=schema_user)

        # true when `setup_test_data.py` run after build
        assert ds['id'] == 2
        assert ds['username'] == 'jdoe'
        assert ds['is_superuser'] is False
        assert {'id': 2, 'name': 'system:partner-engineers'} in ds['groups']


# /api/automation-hub/_ui/v1/users/
@pytest.mark.cloud_only
@pytest.mark.api_ui
def test_users_list_insights_access(ansible_config):
    """Check insights mode access to users endpoint"""
    url = "/api/automation-hub/_ui/v1/users/"

    config = ansible_config("basic_user")
    api_client = get_client(config, request_token=True, require_auth=True)

    with pytest.raises(GalaxyError, match=REGEX_403):
        api_client(url, method="GET")

    with pytest.raises(GalaxyError, match=REGEX_403):
        api_client(url, method="POST", args=b"{}")

    config = ansible_config("partner_engineer")
    api_client = get_client(config, request_token=True, require_auth=True)

    resp = api_client(url, method="GET")
    assert "data" in resp.keys()

    with pytest.raises(GalaxyError, match=REGEX_403):
        api_client(url, method="POST", args=b"{}")


# /api/automation-hub/_ui/v1/users/{id}/
@pytest.mark.cloud_only
@pytest.mark.api_ui
def test_users_detail_insights_access(ansible_config):
    """Check insights mode access to users endpoint"""
    url = "/api/automation-hub/_ui/v1/users/1/"

    config = ansible_config("basic_user")
    api_client = get_client(config, request_token=True, require_auth=True)

    with pytest.raises(GalaxyError, match=REGEX_403):
        api_client(url, method="GET")

    with pytest.raises(GalaxyError, match=REGEX_403):
        api_client(url, method="PUT")

    with pytest.raises(GalaxyError, match=REGEX_403):
        api_client(url, method="DELETE")

    config = ansible_config("partner_engineer")
    api_client = get_client(config, request_token=True, require_auth=True)

    user = api_client(url, method="GET")
    assert user["id"] == 1

    put_resp = api_client(url, method="PUT", args=user)
    assert put_resp == user

    with pytest.raises(GalaxyError, match=REGEX_403):
        api_client(url, method="DELETE")
