#!/usr/bin/env python3

import pytest
from jsonschema import validate as validate_json

from galaxykit.container_images import get_container_images, get_container_readme, \
    put_container_readme, get_container_tags, get_containers
from galaxykit.containers import delete_container
from galaxykit.utils import wait_for_task
from ..schemas import (
    schema_objectlist,
    schema_pulp_objectlist,
    schema_pulp_container_namespace_detail,
    schema_remote_readme
)
from ..utils.rbac_utils import create_local_image_container


# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/_content/history/
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_api_v3_plugin_execution_environments_repositories_content_history(
    ansible_config,
    galaxy_client
):
    gc = galaxy_client("admin")
    name = create_local_image_container(ansible_config("admin"), gc)

    # get the view
    resp = gc.get(f'v3/plugin/execution-environments/repositories/{name}/_content/history/')

    # assert the correct response serializer
    validate_json(instance=resp, schema=schema_objectlist)

    # assert on the expected minimum length of the dataset
    assert resp['data'][0]['number'] >= 1


# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/_content/images/
# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/_content/images/{manifest_ref}/  # noqa: E501
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_api_v3_plugin_execution_environments_repositories_content_images(
    ansible_config,
    galaxy_client
):
    gc = galaxy_client("admin")
    name = create_local_image_container(ansible_config("admin"), gc)
    # get the view
    resp = get_container_images(gc, name)

    # assert the correct response serializer
    validate_json(instance=resp, schema=schema_objectlist)

    # assert we have the pulp object we're expecting
    assert resp['data'][0]['id']


# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/_content/readme/
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_api_v3_plugin_execution_environments_repositories_content_readme(
    ansible_config,
    galaxy_client
):
    gc = galaxy_client("admin")
    name = create_local_image_container(ansible_config("admin"), gc)
    resp = get_container_readme(gc, name)

    print(f'\n\n\n resp:{resp} \n\n\n')

    # assert the correct response serializer
    validate_json(instance=resp, schema=schema_remote_readme)

    # assert the readme is currently an empty string
    assert resp['text'] == ''

    # update the readme
    updated_text = 'Informative text goes here'
    update_resp = put_container_readme(gc, name, data={'text': updated_text})
    assert update_resp['text'] == updated_text

    validate_json(instance=resp, schema=schema_remote_readme)

    # check for the updated readme
    resp = get_container_readme(gc, name)

    # assert the correct response serializer
    validate_json(instance=resp, schema=schema_remote_readme)

    # assert the readme matches the updated text
    assert resp['text'] == updated_text
    assert 'created_at' in resp
    assert 'updated_at' in resp

    delete_response = delete_container(gc, name)
    resp = wait_for_task(gc, delete_response.json(), timeout=10000)
    assert resp["state"] == "completed"


# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/_content/tags/
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_api_v3_plugin_execution_environments_repositories_content_tags(
    ansible_config,
    galaxy_client
):
    gc = galaxy_client("admin")
    name = create_local_image_container(ansible_config("admin"), gc)
    resp = get_container_tags(gc, name)
    manifest = get_container_images(gc, name)
    # assert the correct response serializer
    validate_json(instance=resp, schema=schema_objectlist)

    # assert on the expected number of tags, object and actual tag
    assert len(resp['data']) == 1
    assert resp['data'][0]['tagged_manifest']['pulp_id'] == manifest["data"][0]['id']
    assert resp['data'][0]['name'] in manifest["data"][0]['tags']


# /api/automation-hub/v3/plugin/execution-environments/repositories/
# /api/automation-hub/v3/plugin/execution-environments/repositories/{base_path}/
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_api_v3_plugin_execution_environments_repositories(ansible_config, galaxy_client):
    ns_name = "ns_name_test_ch"
    name = "ee_name_test_ch"

    gc = galaxy_client("admin")
    name = create_local_image_container(ansible_config("admin"), gc, name=f"{ns_name}/{name}")

    # get the ee repositories view
    repository_resp = gc.get('v3/plugin/execution-environments/repositories/?limit=100')

    # assert the correct response serializer
    validate_json(instance=repository_resp, schema=schema_objectlist)

    # validate new repository was created
    repository_names = [x['name'] for x in repository_resp['data']]
    assert name in repository_names

    # get the repository using the base_path
    repository_resp = gc.get(f'v3/plugin/execution-environments/repositories/{name}/')

    assert repository_resp['name'] == name

    # assert existing namespace in repo
    assert repository_resp['namespace']['name'] in name

    # get the namespaces list
    namespace_resp = gc.get('pulp/api/v3/pulp_container/namespaces/')
    assert len(namespace_resp['results']) >= 1

    validate_json(instance=namespace_resp, schema=schema_pulp_objectlist)

    # assert new namespace was created
    assert ns_name in [x['name'] for x in namespace_resp['results']]

    namespace_id = repository_resp['namespace']['id']
    ns_detail_resp = gc.get(f'pulp/api/v3/pulp_container/namespaces/{namespace_id}/')
    validate_json(instance=ns_detail_resp, schema=schema_pulp_container_namespace_detail)

    # assert new namespace was created
    assert ns_name == ns_detail_resp['name']

    # assert pulp_labels dictionary is in response
    assert type(repository_resp['pulp']['repository']['pulp_labels']) is dict

    # delete the repository
    delete_response = delete_container(gc, name)
    resp = wait_for_task(gc, delete_response.json(), timeout=10000)
    assert resp["state"] == "completed"

    # # get the repositories list again
    repository_resp = get_containers(gc)

    # assert the new repository has been deleted
    repository_names = [x['name'] for x in repository_resp['data']]

    assert name not in repository_names
