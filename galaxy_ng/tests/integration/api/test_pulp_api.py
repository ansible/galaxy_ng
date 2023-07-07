import random
import string

import pytest
from ansible.galaxy.api import AnsibleError, GalaxyError
from jsonschema import validate as validate_json

from .rbac_actions.utils import ReusableLocalContainer
from ..schemas import schema_pulp_objectlist, schema_pulp_roledetail, schema_task_detail
from ..utils import get_client, wait_for_task

REGEX_40X = r"HTTP Code: 40\d"


@pytest.mark.deployment_standalone
@pytest.mark.pulp_api
@pytest.mark.min_hub_version("4.6dev")
def test_pulp_api_redirect(ansible_config, artifact):
    """Test that /pulp/ is redirecting to /api/galaxy/pulp/"""

    config = ansible_config("admin")

    api_client = get_client(config=config, request_token=True, require_auth=True)

    # verify api root works
    response = api_client("/pulp/api/v3/")
    assert "users" in response

    # verify a couple of different paths work
    response = api_client("/pulp/api/v3/status/")
    assert "versions" in response

    response = api_client("/pulp/api/v3/distributions/ansible/ansible/")
    assert response["count"] > 0

    # verify query params work
    response = api_client("/pulp/api/v3/distributions/ansible/ansible/?name=published")
    assert response["count"] == 1

    # verify the hrefs are not returning the old url
    assert not response["results"][0]["pulp_href"].startswith("/pulp/")


@pytest.mark.parametrize(
    "url",
    [
        "{api_prefix}/pulp/api/v3/repositories/ansible/ansible/",
        "{api_prefix}/pulp/api/v3/roles/",
    ],
)
@pytest.mark.pulp_api
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.all
def test_pulp_endpoint_readonly(ansible_config, artifact, url):
    """Ensure authenticated user has readonly access to view"""

    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(config, request_token=True, require_auth=True)

    # NOTE: with `count` this only applies to lists, can be adjusted for future views
    url = url.format(api_prefix=api_prefix)
    response = api_client(url, method="GET")
    assert "count" in response

    with pytest.raises(GalaxyError, match=REGEX_40X):
        api_client(url, method="POST")

    with pytest.raises(GalaxyError, match=REGEX_40X):
        api_client(url, method="PUT")

    with pytest.raises(GalaxyError, match=REGEX_40X):
        api_client(url, method="DELETE")


TEST_ROLE_NAME = "test_role_".join(random.choices(string.ascii_lowercase, k=10))


@pytest.mark.parametrize(
    "require_auth",
    [
        True,
        # False,
    ],
)
@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.6dev")
def test_pulp_roles_endpoint(ansible_config, require_auth):
    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(config, request_token=True, require_auth=require_auth)

    permission = "galaxy.add_group"
    payload = {
        "name": TEST_ROLE_NAME,
        "permissions": [permission],
    }

    # create a role
    create_resp = api_client(
        f"{api_prefix}/pulp/api/v3/roles/",
        args=payload,
        method="POST"
    )
    assert TEST_ROLE_NAME == create_resp["name"]
    assert permission in create_resp["permissions"]
    pulp_href = f"{create_resp['pulp_href']}"

    # list roles
    list_response = api_client(f"{api_prefix}/pulp/api/v3/roles/", method="GET")
    validate_json(instance=list_response, schema=schema_pulp_objectlist)
    list_ds = list_response["results"]
    role_names = [x['name'] for x in list_ds]

    # validate the new one shows up
    assert TEST_ROLE_NAME in role_names

    # update the role
    description = "Description goes here."
    payload = {"description": description}
    api_client(pulp_href, args=payload, method="PATCH")

    # verify updated role
    get_resp = api_client(pulp_href, method="GET")
    validate_json(instance=get_resp, schema=schema_pulp_roledetail)
    assert get_resp["description"] == description

    # delete the role
    try:
        api_client(pulp_href, method="DELETE")
    except AnsibleError:
        # no response object when deleting throws an error with api_client

        # verify the role has been deleted
        list_response = api_client(f"{api_prefix}/pulp/api/v3/roles/", method="GET")
        list_ds = list_response["results"]
        role_names = [x['name'] for x in list_ds]

        # validate the role has been deleted
        assert TEST_ROLE_NAME not in role_names


@pytest.fixture
def local_container():
    return ReusableLocalContainer('int_tests')


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

    wait_for_task(api_client, delete_resp)
    with pytest.raises(GalaxyError, match=REGEX_40X):
        api_client(
            f"{api_prefix}/v3/plugin/execution-environments/repositories/{name}/", method="GET")
