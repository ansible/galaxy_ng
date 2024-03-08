import random
import string

import pytest
from ansible.galaxy.api import GalaxyError
from jsonschema import validate as validate_json

from galaxykit.utils import wait_for_task, GalaxyClientError
from .rbac_actions.utils import ReusableLocalContainer
from ..schemas import schema_pulp_objectlist, schema_pulp_roledetail, schema_task_detail
from ..utils import get_client, wait_for_task as wait_for_task_gng
from ..utils.rbac_utils import create_emtpy_local_image_container

REGEX_40X = r"HTTP Code: 40\d"


@pytest.fixture
def local_container(galaxy_client):
    gc = galaxy_client("admin", ignore_cache=True)
    return ReusableLocalContainer('int_tests', gc)


@pytest.mark.deployment_standalone
@pytest.mark.pulp_api
@pytest.mark.min_hub_version("4.6dev")
def test_pulp_api_redirect(galaxy_client):
    """Test that /pulp/ is redirecting to /api/galaxy/pulp/"""

    gc = galaxy_client("admin")
    # verify api root works
    response = gc.get("pulp/api/v3/")
    assert "users" in response

    # verify a couple of different paths work
    response = gc.get("pulp/api/v3/status/")
    assert "versions" in response

    response = gc.get("pulp/api/v3/distributions/ansible/ansible/")
    assert response["count"] > 0

    # verify query params work
    response = gc.get("pulp/api/v3/distributions/ansible/ansible/?name=published")
    assert response["count"] == 1

    # verify the hrefs are not returning the old url
    assert not response["results"][0]["pulp_href"].startswith("/pulp/")


@pytest.mark.parametrize(
    "url",
    [
        "pulp/api/v3/repositories/ansible/ansible/",
        "pulp/api/v3/roles/",
    ],
)
@pytest.mark.pulp_api
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.all
def test_pulp_endpoint_readonly(galaxy_client, url):
    """Ensure authenticated user has readonly access to view"""

    gc = galaxy_client("admin")

    # NOTE: with `count` this only applies to lists, can be adjusted for future views
    response = gc.get(url)
    assert "count" in response

    with pytest.raises(GalaxyClientError) as e:
        gc.post(url, body={})
    assert e.value.response.status_code == 400

    with pytest.raises(GalaxyClientError) as e:
        gc.post(url, body={})
    assert e.value.response.status_code == 400

    with pytest.raises(GalaxyClientError) as e:
        gc.post(url, body={})
    assert e.value.response.status_code == 400


TEST_ROLE_NAME = "test_role_".join(random.choices(string.ascii_lowercase, k=10))


@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.6dev")
def test_pulp_roles_endpoint(galaxy_client):
    gc = galaxy_client("admin")

    permission = "galaxy.add_group"
    payload = {
        "name": TEST_ROLE_NAME,
        "permissions": [permission],
    }

    # create a role
    create_resp = gc.post(
        "pulp/api/v3/roles/",
        body=payload
    )
    assert TEST_ROLE_NAME == create_resp["name"]
    assert permission in create_resp["permissions"]
    pulp_href = f"{create_resp['pulp_href']}"

    # list roles
    list_response = gc.get("pulp/api/v3/roles/")
    validate_json(instance=list_response, schema=schema_pulp_objectlist)
    list_ds = list_response["results"]
    role_names = [x['name'] for x in list_ds]

    # validate the new one shows up
    assert TEST_ROLE_NAME in role_names

    # update the role
    description = "Description goes here."
    payload = {"description": description}
    gc.patch(pulp_href, body=payload)

    # verify updated role
    get_resp = gc.get(pulp_href)
    validate_json(instance=get_resp, schema=schema_pulp_roledetail)
    assert get_resp["description"] == description

    # delete the role
    gc.delete(pulp_href, parse_json=False)

    # verify the role has been deleted
    list_response = gc.get("pulp/api/v3/roles/")
    list_ds = list_response["results"]
    role_names = [x['name'] for x in list_ds]

    # validate the role has been deleted
    assert TEST_ROLE_NAME not in role_names


@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_gw_pulp_task_endpoint(galaxy_client, ansible_config):

    gc = galaxy_client("ee_admin")

    name = create_emtpy_local_image_container(ansible_config("admin"), gc)

    delete_resp = gc.delete(
        f"v3/plugin/execution-environments/repositories/{name}/", relogin=False
    )
    task_url = delete_resp["task"]

    task_detail = gc.get(task_url, relogin=False)
    validate_json(instance=task_detail, schema=schema_task_detail)

    wait_for_task(gc, delete_resp)
    with pytest.raises(GalaxyClientError) as e:
        gc.get(f"v3/plugin/execution-environments/repositories/{name}/")
    assert e.value.response.status_code == 404


@pytest.mark.parametrize(
    "require_auth",
    [
        True,
        False,
    ],
)
@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
@pytest.mark.skip_in_gw
def test_pulp_task_endpoint(ansible_config, local_container, require_auth):
    name = local_container.get_container()['name']
    config = ansible_config("ee_admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(config, request_token=True, require_auth=require_auth)

    delete_resp = api_client(
        f"{api_prefix}/v3/plugin/execution-environments/repositories/{name}/", method="DELETE"
    )
    task_url = delete_resp["task"][len(f'{api_prefix}/'):]

    task_detail = api_client(f"{api_prefix}/{task_url}", method="GET")
    validate_json(instance=task_detail, schema=schema_task_detail)

    wait_for_task_gng(api_client, delete_resp)
    with pytest.raises(GalaxyError, match=REGEX_40X):
        api_client(
            f"{api_prefix}/v3/plugin/execution-environments/repositories/{name}/", method="GET")
