#!/usr/bin/env python3

import pytest
from jsonschema import validate as validate_json

from ..schemas import (
    schema_objectlist,
    schema_pulp_objectlist,
    schema_pulp_container_namespace_detail,
    schema_remote_readme
)
from ..utils import wait_for_task, get_client
from .rbac_actions.utils import ReusableLocalContainer


@pytest.fixture
def local_container():
    return ReusableLocalContainer('int_tests')


# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/_content/history/
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_api_v3_plugin_execution_environments_repositories_content_history(
    ansible_config,
    local_container
):
    name = local_container.get_container()['name']
    cfg = ansible_config('ee_admin')
    api_prefix = cfg.get("api_prefix").rstrip("/")
    api_client = get_client(cfg)

    # get the view
    resp = api_client(
        f'{api_prefix}/v3/plugin/execution-environments/repositories/{name}/_content/history/',
        method="GET")

    # assert the correct response serializer
    validate_json(instance=resp, schema=schema_objectlist)

    # assert on the expected minimum length of the dataset
    assert resp['data'][0]['number'] >= 1


# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/_content/images/
# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/_content/images/{manifest_ref}/
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_api_v3_plugin_execution_environments_repositories_content_images(
    ansible_config,
    local_container
):
    name = local_container.get_container()['name']
    manifest = local_container.get_manifest()
    cfg = ansible_config('ee_admin')
    api_prefix = cfg.get("api_prefix").rstrip("/")
    api_client = get_client(cfg)
    # get the view
    resp = api_client(
        f'{api_prefix}/v3/plugin/execution-environments/repositories/{name}/_content/images/'
    )

    # assert the correct response serializer
    validate_json(instance=resp, schema=schema_objectlist)

    # assert we have the pulp object we're expecting
    assert resp['data'][0]['id'] == manifest['id']


# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/_content/readme/
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_api_v3_plugin_execution_environments_repositories_content_readme(
    ansible_config,
    local_container
):
    name = local_container.get_container()['name']
    cfg = ansible_config('ee_admin')
    api_prefix = cfg.get("api_prefix").rstrip("/")
    url = f'{api_prefix}/v3/plugin/execution-environments/repositories/{name}/_content/readme/'
    api_client = get_client(cfg)
    # get the view
    resp = api_client(url, method="GET")
    print(f'\n\n\n resp:{resp} \n\n\n')

    # assert the correct response serializer
    validate_json(instance=resp, schema=schema_remote_readme)

    # assert the readme is currently an empty string
    assert resp['text'] == ''

    # update the readme
    updated_text = 'Informative text goes here'
    update_resp = api_client(url, args={'text': updated_text}, method="PUT")
    assert update_resp['text'] == updated_text

    validate_json(instance=resp, schema=schema_remote_readme)

    # check for the updated readme
    resp = api_client(url, method="GET")

    # assert the correct response serializer
    validate_json(instance=resp, schema=schema_remote_readme)

    # assert the readme matches the updated text
    assert resp['text'] == updated_text
    assert 'created_at' in resp
    assert 'updated_at' in resp

    delete_response = api_client(f"{api_prefix}/v3/plugin/execution-environments/"
                                 f"repositories/{name}/", method='DELETE')
    resp = wait_for_task(api_client, delete_response, timeout=10000)
    assert resp["state"] == "completed"


# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/_content/tags/
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_api_v3_plugin_execution_environments_repositories_content_tags(
    ansible_config,
    local_container
):
    manifest = local_container.get_manifest()
    name = local_container.get_container()['name']
    cfg = ansible_config('ee_admin')
    api_prefix = cfg.get("api_prefix").rstrip("/")
    api_client = get_client(cfg)

    # get the view
    resp = api_client(
        f'{api_prefix}/v3/plugin/execution-environments/repositories/{name}/_content/tags/',
        method="GET")

    # assert the correct response serializer
    validate_json(instance=resp, schema=schema_objectlist)

    # assert on the expected number of tags, object and actual tag
    assert len(resp['data']) == 1
    assert resp['data'][0]['tagged_manifest']['pulp_id'] == manifest['id']
    assert resp['data'][0]['name'] in manifest['tags']


# /api/automation-hub/v3/plugin/execution-environments/repositories/
# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_api_v3_plugin_execution_environments_repositories(ansible_config, local_container):
    ns_name = local_container.get_namespace()['name']
    name = local_container.get_container()['name']
    cfg = ansible_config('admin')
    api_prefix = cfg.get("api_prefix").rstrip("/")
    api_client = get_client(cfg)

    # get the ee repositories view
    repository_resp = api_client(
        f'{api_prefix}/v3/plugin/execution-environments/repositories/?limit=100',
        method="GET"
    )

    # assert the correct response serializer
    validate_json(instance=repository_resp, schema=schema_objectlist)

    # validate new repository was created
    repository_names = [x['name'] for x in repository_resp['data']]
    assert name in repository_names

    # get the repository using the base_path
    repository_resp = api_client(
        f'v3/plugin/execution-environments/repositories/{name}/', method="GET"
    )

    assert repository_resp['name'] == name

    # assert existing namespace in repo
    assert repository_resp['namespace']['name'] in name

    # get the namespaces list
    namespace_resp = api_client('pulp/api/v3/pulp_container/namespaces/', method='GET')
    assert len(namespace_resp['results']) >= 1

    validate_json(instance=namespace_resp, schema=schema_pulp_objectlist)

    # assert new namespace was created
    assert ns_name in [x['name'] for x in namespace_resp['results']]

    namespace_id = repository_resp['namespace']['id']
    ns_detail_resp = api_client(
        f'pulp/api/v3/pulp_container/namespaces/{namespace_id}', method="GET")
    validate_json(instance=ns_detail_resp, schema=schema_pulp_container_namespace_detail)

    # assert new namespace was created
    assert ns_name == ns_detail_resp['name']

    # assert pulp_labels dictionary is in response
    assert type(repository_resp['pulp']['repository']['pulp_labels']) is dict

    # delete the repository
    delete_repository_resp = api_client(
        f'{api_prefix}/v3/plugin/execution-environments/repositories/{name}/',
        method="DELETE"
    )
    # assert delete_repository_resp.status_code == 202
    task = delete_repository_resp
    wait_for_task(api_client, task)

    # # get the repositories list again
    repository_resp = api_client(
        f'{api_prefix}/v3/plugin/execution-environments/repositories/',
        method="GET"
    )

    # assert the new repository has been deleted
    repository_names = [x['name'] for x in repository_resp['data']]

    assert name not in repository_names
