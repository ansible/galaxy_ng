#!/usr/bin/env python3

import os
import random
import pytest
from jsonschema import validate as validate_json

from galaxykit.utils import GalaxyClientError
from ..constants import DEFAULT_DISTROS
from ..schemas import (
    schema_collection_import,
    schema_collection_import_detail,
    schema_collectionversion,
    schema_collectionversion_metadata,
    schema_distro,
    schema_distro_repository,
    schema_ee_registry,
    schema_featureflags,
    schema_group,
    schema_me,
    schema_namespace_detail,
    schema_objectlist,
    schema_remote,
    schema_settings,
    schema_task,
    schema_ui_collection_summary,
    schema_user,
)
from ..utils import generate_unused_namespace, wait_for_task_ui_client
from ..utils.iqe_utils import get_paginated, remove_from_cache, aap_gateway


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_login(galaxy_client):
    gc = galaxy_client("basic_user", ignore_cache=True)

    # an authenticated session has a csrftoken and a sessionid
    assert gc.cookies['csrftoken'] is not None
    assert gc.cookies['gateway_sessionid'] is not None


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_logout(galaxy_client):
    gc = galaxy_client("basic_user", ignore_cache=True)

    # check the auth first
    assert gc.cookies['csrftoken'] is not None
    assert gc.cookies['gateway_sessionid'] is not None

    gc.gw_client.logout()

    # logout should clear the sessionid but not the csrftoken
    assert gc.gw_client.cookies['csrftoken'] is not None
    assert 'sessionid' not in gc.gw_client.cookies
    remove_from_cache("basic_user")


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_collection_versions(galaxy_client, uncertifiedv2):
    gc = galaxy_client('basic_user')
    ds = gc.get('_ui/v1/collection-versions/')
    validate_json(instance=ds, schema=schema_objectlist)
    assert len(ds['data']) >= 1
    for cv in ds['data']:
        validate_json(instance=cv, schema=schema_collectionversion)
        validate_json(instance=cv['metadata'], schema=schema_collectionversion_metadata)

        # try to get the direct url for this version ...
        cv_url = f"_ui/v1/collection-versions/{cv['namespace']}/{cv['name']}/{cv['version']}/"
        cv_resp = gc.get(cv_url)
        validate_json(instance=cv_resp, schema=schema_collectionversion)
        validate_json(instance=cv_resp['metadata'], schema=schema_collectionversion_metadata)


# FIXME: unskip when https://issues.redhat.com/browse/AAP-32675 is merged
@pytest.mark.skip_in_gw
@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_collection_versions_version_range(galaxy_client, uncertifiedv2):
    """Test the ?version_range query parameter."""
    c1, c2 = uncertifiedv2
    gc = galaxy_client('basic_user')
    v_path = f"_ui/v1/collection-versions/?name={c1.name}&namespace={c1.namespace}"

    # test single version
    ds = gc.get(f'{v_path}&version_range=={c1.version}')
    assert len(ds['data']) == 1
    assert ds['data'][0]["version"] == c1.version

    # test range
    ds = gc.get(f'{v_path}&version_range>={c1.version}')
    assert len(ds['data']) == 2
    assert set([v["version"] for v in ds['data']]) == set([c1.version, c2.version])

    # test range exclusive
    ds = gc.get(f'{v_path}&version_range=>{c1.version}')
    assert len(ds['data']) == 1
    assert ds['data'][0]["version"] == c2.version

    # test invalid
    with pytest.raises(GalaxyClientError) as ctx:
        gc.get(f'{v_path}&version_range=not_a_semver_version')
    assert ctx.value.response.status_code == 400


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_distributions(galaxy_client):
    gc = galaxy_client('basic_user')
    ds = gc.get('_ui/v1/distributions/?limit=1000')
    validate_json(instance=ds, schema=schema_objectlist)

    for distro in ds['data']:
        validate_json(instance=distro, schema=schema_distro)
        if distro['repository']:
            validate_json(instance=distro['repository'], schema=schema_distro_repository)

    distros_to_remove = []
    for distro in ds['data']:
        if distro["name"].startswith("repo-test-") or distro["name"].startswith("dist-test-"):
            distros_to_remove.append(distro)
    for distro in distros_to_remove:
        ds['data'].remove(distro)

    # make sure all default distros are in the list ...
    distro_tuples = [(x['name'], x['base_path']) for x in ds['data']]
    for k, v in DEFAULT_DISTROS.items():
        key = (k, v['basepath'])
        # this next assert might fail if the test suite has been run before against
        # the same hub instance
        # https://issues.redhat.com/browse/AAH-2601
        try:
            assert key in distro_tuples
        except AssertionError:
            pytest.xfail("rh-certified distribution has not been found because "
                         "the distribution endpoint returns the first 100 distributions"
                         " and rh-certified is further down in the list. "
                         "This has happened because the whole test suite has been run"
                         " multiple times against the same hub instance, "
                         "leaving a lot of test data. "
                         "This is the jira to fix the test: AAH-2601")


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_distributions_by_id(galaxy_client):
    gc = galaxy_client('basic_user')
    # get the response
    ds = gc.get('_ui/v1/distributions/')
    validate_json(instance=ds, schema=schema_objectlist)

    for distro in ds['data']:
        validate_json(instance=distro, schema=schema_distro)

    # check the endpoint for each distro by pulp id ...
    distro_ids = [x['pulp_id'] for x in ds['data']]
    for distro_id in distro_ids:
        _ds = gc.get(f'_ui/v1/distributions/{distro_id}/')
        validate_json(instance=_ds, schema=schema_distro)
        if _ds['repository']:
            validate_json(instance=_ds['repository'], schema=schema_distro_repository)
        assert _ds['pulp_id'] == distro_id


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_execution_environments_registries(galaxy_client):
    gc = galaxy_client('ee_admin')

    # get the response
    ds = gc.get('_ui/v1/execution-environments/registries/')
    validate_json(instance=ds, schema=schema_objectlist)

    # try to create one
    suffix = random.choice(range(0, 1000))
    rname = f'redhat.io.{suffix}'
    payload = {
        'name': rname,
        'url': 'https://registry.redhat.io',
    }
    rds = gc.post('_ui/v1/execution-environments/registries/', body=payload)
    validate_json(instance=rds, schema=schema_ee_registry)
    try:
        id = rds["id"]
    except KeyError:
        id = rds["pk"]

    # try to get it by pulp_id
    rds = gc.get(f"_ui/v1/execution-environments/registries/{id}/")
    validate_json(instance=rds, schema=schema_ee_registry)
    try:
        id = rds["id"]
    except KeyError:
        id = rds["pk"]
    # sync it
    task = gc.post(
        f"_ui/v1/execution-environments/registries/{id}/sync/",
        body={}
    )
    validate_json(instance=task, schema=schema_task)

    # wait for sync to finish
    wait_for_task_ui_client(gc, task)

    # index it
    task = gc.post(
        f"_ui/v1/execution-environments/registries/{id}/index/",
        body={}
    )
    validate_json(instance=task, schema=schema_task)

    # wait for index to finish
    wait_for_task_ui_client(gc, task)

    # delete the registry
    gc.delete(f"_ui/v1/execution-environments/registries/{id}/", parse_json=False)

    # make sure it's gone
    with pytest.raises(GalaxyClientError) as ctx:
        gc.get(f"_ui/v1/execution-environments/registries/{id}/")
    assert ctx.value.response.status_code == 404


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_feature_flags(galaxy_client):

    gc = galaxy_client('basic_user')
    # get the response
    ds = gc.get('_ui/v1/feature-flags/')
    validate_json(instance=ds, schema=schema_featureflags)

    # assert ds['ai_deny_index'] is False
    assert ds['execution_environments'] is True
    assert ds['legacy_roles'] is False


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
@pytest.mark.skipif(
    os.getenv("ENABLE_DAB_TESTS"),
    reason="Skipping test because this is broken with dab_jwt"
)
@pytest.mark.skip(reason="groups can't be created in hub anymore")
def test_gw_api_ui_v1_groups_users(galaxy_client):

    gc = galaxy_client('basic_user')
    groups_ds = gc.get('_ui/v1/groups/?limit=1000')
    validate_json(instance=groups_ds, schema=schema_objectlist)

    # get the primary key for PE
    pe_id = None
    for x in groups_ds['data']:
        if x['name'] == 'system:partner-engineers':
            pe_id = x['id']
            break
    assert pe_id is not None

    # validate username="jdoe" is in the group's userlist
    users_ds = gc.get(f'_ui/v1/groups/{pe_id}/users/')
    validate_json(instance=users_ds, schema=schema_objectlist)
    assert "jdoe" in [x["username"] for x in users_ds["data"]]


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_groups_by_id(galaxy_client):

    gc = galaxy_client('basic_user')
    # get the response
    ds = gc.get('_ui/v1/groups/')
    validate_json(instance=ds, schema=schema_objectlist)

    for grp in ds['data']:
        gid = grp['id']
        ds = gc.get(f'_ui/v1/groups/{gid}/')
        validate_json(instance=ds, schema=schema_group)
        assert ds['id'] == gid


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_imports_collections(galaxy_client):
    gc = galaxy_client('basic_user')
    # get the response
    ds = gc.get('_ui/v1/imports/collections/')
    validate_json(instance=ds, schema=schema_objectlist)

    for job in ds['data']:
        validate_json(instance=job, schema=schema_collection_import)
        task_id = job['id']
        jurl = f'_ui/v1/imports/collections/{task_id}/'
        jds = gc.get(jurl)
        validate_json(instance=jds, schema=schema_collection_import_detail)


@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_me(galaxy_client, settings):
    gc = galaxy_client('basic_user')
    # get the response
    ds = gc.get('_ui/v1/me/')
    validate_json(instance=ds, schema=schema_me)

    assert not ds['is_anonymous']
    assert ds['username'] == ds.get('username')

    if settings.get("KEYCLOAK_URL") is not None:
        assert ds['auth_provider'] == ['keycloak']
    else:
        assert ds['auth_provider'] == ['django']


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
@pytest.mark.skip(reason="groups can't be created in hub anymore")
def test_gw_api_ui_v1_my_namespaces(galaxy_client):
    gc = galaxy_client("partner_engineer")
    new_namespace = generate_unused_namespace(gc, api_version='_ui/v1')

    # get user
    ds = gc.get('_ui/v1/me/')

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
    gc.post('_ui/v1/my-namespaces/', body=payload)

    # get the my-namespaces view
    ds = gc.get('_ui/v1/my-namespaces/')
    validate_json(instance=ds, schema=schema_objectlist)

    # get all the namespaces in the view
    namespace_names = get_paginated(gc, '_ui/v1/my-namespaces/')
    namespace_names = [x['name'] for x in namespace_names]

    # validate the new one shows up
    for expected_ns_name in ['autohubtest2', 'autohubtest3', 'signing', new_namespace]:
        assert expected_ns_name in namespace_names

    # delete
    gc.delete(f'_ui/v1/my-namespaces/{new_namespace}/', parse_json=False)

    # get the response
    gc.get('_ui/v1/my-namespaces/')

    # confirm deletion
    namespace_names = get_paginated(gc, '_ui/v1/my-namespaces/')
    namespace_names = [x['name'] for x in namespace_names]
    assert new_namespace not in namespace_names


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_my_namespaces_name(galaxy_client):
    gc = galaxy_client('partner_engineer')
    # get the response
    resp = gc.get('_ui/v1/my-namespaces/autohubtest2/')
    validate_json(instance=resp, schema=schema_namespace_detail)


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_remotes(galaxy_client):
    gc = galaxy_client('basic_user')
    # get the response
    ds = gc.get('_ui/v1/remotes/?limit=100')
    validate_json(instance=ds, schema=schema_objectlist)

    for remote in ds['data']:
        validate_json(instance=remote, schema=schema_remote)

    remote_names = [x['name'] for x in ds['data']]
    assert 'community' in remote_names
    assert 'rh-certified' in remote_names


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_remotes_by_id(galaxy_client):

    gc = galaxy_client('basic_user')
    # get the response
    ds = gc.get('_ui/v1/remotes/')
    validate_json(instance=ds, schema=schema_objectlist)

    for remote in ds['data']:
        validate_json(instance=remote, schema=schema_remote)

    # FIXME - there is no suitable pulp_id for a remote?
    pulp_ids = [x['pk'] for x in ds['data']]
    for pulp_id in pulp_ids:
        gc.get(f'_ui/v1/remotes/{pulp_id}/')


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_repo_distro_by_basepath(galaxy_client):

    gc = galaxy_client('basic_user')
    # get each repo by basepath? or is it get a distro by basepath?
    for v in DEFAULT_DISTROS.values():
        bp = v['basepath']
        ds = gc.get(f'_ui/v1/repo/{bp}/')
        validate_json(instance=ds, schema=schema_objectlist)


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_collection_detail_view(galaxy_client, published):

    namespace = published.namespace
    name = published.name
    version = published.version

    gc = galaxy_client('basic_user')
    ds = gc.get(f'_ui/v1/repo/published/{namespace}/{name}/')
    validate_json(instance=ds, schema=schema_ui_collection_summary)

    assert ds['namespace']['name'] == namespace
    assert ds['name'] == name
    assert ds['latest_version']['version'] == version
    all_versions = [x['version'] for x in ds['all_versions']]
    assert version in all_versions


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_settings(galaxy_client):
    gc = galaxy_client('basic_user')

    # get the response
    ds = gc.get('_ui/v1/settings/')
    validate_json(instance=ds, schema=schema_settings)

    # FIXME - password length and token expiration are None?
    assert ds['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS'] is False
    assert ds['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD'] is False
    assert ds['GALAXY_REQUIRE_CONTENT_APPROVAL'] is True


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_api_ui_v1_tags(galaxy_client):

    gc = galaxy_client('basic_user')

    # get the response
    ds = gc.get('_ui/v1/tags/')
    validate_json(instance=ds, schema=schema_objectlist)

    # FIXME - ui tags api does not support POST?


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
@pytest.mark.skipif(
    os.getenv("ENABLE_DAB_TESTS"),
    reason="Skipping test because this is broken with dab_jwt"
)
def test_gw_api_ui_v1_users_by_id(galaxy_client):
    gc = galaxy_client('partner_engineer')
    resp = gc.get('_ui/v1/users/?username=jdoe')
    id = resp["data"][0]["id"]

    # there's no groups as they cannot be created directly in the hub
    # resp = gc.get('_ui/v1/groups/?name=system:partner-engineers')
    # group_id = resp["data"][0]["id"]

    # get the response
    ds = gc.get(f'_ui/v1/users/{id}/')
    validate_json(instance=ds, schema=schema_user)

    assert ds['id'] == id
    assert ds['username'] == 'jdoe'
    # assert ds['is_superuser'] is False
    # assert {'id': group_id, 'name': 'system:partner-engineers'} in ds['groups']
