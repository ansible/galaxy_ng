"""test_namespace_management.py - Test related to namespaces.

See: https://issues.redhat.com/browse/AAH-1303

"""
import pytest
from ansible.errors import AnsibleError

from ..utils import get_client
from ..utils import generate_unused_namespace
from ..utils import get_all_namespaces
from ..utils import wait_for_all_tasks

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.galaxyapi_smoke
@pytest.mark.namespace
@pytest.mark.parametrize(
    "api_version",
    [
        'v3',
        '_ui/v1'
    ]
)
@pytest.mark.all
def test_namespace_create_and_delete(ansible_config, api_version):
    """Tests whether a namespace can be created and deleted"""

    # http://192.168.1.119:8002/api/automation-hub/_ui/v1/namespaces/
    # http://192.168.1.119:8002/api/automation-hub/v3/namespaces/
    # {name: "testnamespace1", groups: []}

    config = ansible_config("partner_engineer")
    api_client = get_client(config, request_token=True, require_auth=True)
    api_prefix = config.get("api_prefix").rstrip("/")

    new_namespace = generate_unused_namespace(api_client=api_client, api_version=api_version)
    payload = {'name': new_namespace, 'groups': []}
    resp = api_client(f'{api_prefix}/{api_version}/namespaces/', args=payload, method='POST')
    assert resp['name'] == new_namespace

    existing2 = get_all_namespaces(api_client=api_client, api_version=api_version)
    existing2 = dict((x['name'], x) for x in existing2)
    assert new_namespace in existing2

    # This should throw an AnsibleError because the response body is an
    # empty string and can not be parsed to JSON
    try:
        resp = api_client(
            f'{api_prefix}/{api_version}/namespaces/{new_namespace}/',
            method='DELETE'
        )
    except AnsibleError:
        pass

    existing3 = get_all_namespaces(api_client=api_client, api_version=api_version)
    existing3 = dict((x['name'], x) for x in existing3)
    assert new_namespace not in existing3


@pytest.mark.galaxyapi_smoke
@pytest.mark.namespace
@pytest.mark.all
@pytest.mark.parametrize(
    "user_property",
    [
        'id',
        'username'
    ]
)
@pytest.mark.min_hub_version("4.9")
def test_namespace_create_with_user(ansible_config, user_property):
    config = ansible_config("partner_engineer")
    api_client = get_client(config, request_token=True, require_auth=True)
    api_prefix = config.get("api_prefix").rstrip("/")

    # find this client's user info...
    me = api_client(f'{api_prefix}/_ui/v1/me/')
    username = me['username']

    new_namespace = generate_unused_namespace(api_client=api_client)

    # make a namespace with a user and without defining groups ...
    object_roles = [
        'galaxy.collection_namespace_owner',
        'galaxy.collection_publisher'
    ]
    payload = {
        'name': new_namespace,
        'users': [
            {
                user_property: me.get(user_property),
                'object_roles': object_roles,
            }
        ]
    }
    resp = api_client(f'{api_prefix}/_ui/v1/my-namespaces/', args=payload, method='POST')

    # should have the right results ...
    assert resp['name'] == new_namespace
    assert resp['groups'] == []
    assert resp['users'] != []
    assert username in [x['name'] for x in resp['users']]
    assert sorted(resp['users'][0]['object_roles']) == sorted(object_roles)


@pytest.mark.galaxyapi_smoke
@pytest.mark.namespace
@pytest.mark.all
@pytest.mark.parametrize(
    "user_property",
    [
        'id',
        'username'
    ]
)
@pytest.mark.min_hub_version("4.9")
def test_namespace_edit_with_user(ansible_config, user_property):
    config = ansible_config("partner_engineer")
    api_client = get_client(config, request_token=True, require_auth=True)
    api_prefix = config.get("api_prefix").rstrip("/")

    # find this client's user info...
    me = api_client(f'{api_prefix}/_ui/v1/me/')
    username = me['username']

    new_namespace = generate_unused_namespace(api_client=api_client)

    # make a namespace without users and without groups ...
    payload = {
        'name': new_namespace,
    }
    resp = api_client(f'{api_prefix}/_ui/v1/my-namespaces/', args=payload, method='POST')

    # should have the right results ...
    assert resp['name'] == new_namespace
    assert resp['groups'] == []
    assert resp['users'] == []

    # now edit the namespace to add the user
    object_roles = [
        'galaxy.collection_namespace_owner',
        'galaxy.collection_publisher'
    ]
    payload = {
        'name': new_namespace,
        'users': [
            {
                user_property: me.get(user_property),
                'object_roles': object_roles,
            }
        ]
    }
    resp = api_client(
        f'{api_prefix}/_ui/v1/my-namespaces/{new_namespace}/',
        args=payload,
        method='PUT'
    )

    # should have the right results ...
    assert resp['name'] == new_namespace
    assert resp['groups'] == []
    assert resp['users'] != []
    assert username in [x['name'] for x in resp['users']]
    assert sorted(resp['users'][0]['object_roles']) == sorted(object_roles)


@pytest.mark.namespace
@pytest.mark.all
def test_namespace_edit_logo(ansible_config):

    config = ansible_config("admin")
    api_client = get_client(config, request_token=True, require_auth=True)
    api_prefix = config.get("api_prefix").rstrip("/")

    new_namespace = generate_unused_namespace(api_client=api_client)

    payload = {
        'name': new_namespace,
    }
    my_namespace = api_client(f'{api_prefix}/_ui/v1/my-namespaces/', args=payload, method='POST')
    assert my_namespace["avatar_url"] == ''

    namespaces = api_client(f'{api_prefix}/_ui/v1/my-namespaces/')

    name = my_namespace["name"]

    payload = {
        "name": name,
        "avatar_url": "http://placekitten.com/400/400"
    }
    api_client(f'{api_prefix}/_ui/v1/my-namespaces/{name}/', args=payload, method='PUT')

    wait_for_all_tasks(api_client)
    updated_namespace = api_client(f'{api_prefix}/_ui/v1/my-namespaces/{name}/')
    assert updated_namespace["avatar_url"] != ""

    payload = {
        "name": name,
        "avatar_url": "http://placekitten.com/123/456"
    }
    resp = api_client(f'{api_prefix}/_ui/v1/my-namespaces/{name}/', args=payload, method='PUT')

    wait_for_all_tasks(api_client)
    updated_again_namespace = api_client(f'{api_prefix}/_ui/v1/my-namespaces/{name}/')
    assert updated_namespace["avatar_url"] != updated_again_namespace["avatar_url"]

    # verify no additional namespaces are created
    resp = api_client(f'{api_prefix}/_ui/v1/my-namespaces/')
    assert resp["meta"]["count"] == namespaces["meta"]["count"]

    # verify no side effects
    # fields that should NOT change
    for field in ["pulp_href", "name", "company", "email", "description", "resources", "links"]:
        assert my_namespace[field] == updated_again_namespace[field]

    # fields that changed
    for field in ["avatar_url", "metadata_sha256", "avatar_sha256"]:
        assert my_namespace[field] != updated_again_namespace[field]
