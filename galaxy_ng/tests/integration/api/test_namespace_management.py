"""test_namespace_management.py - Test related to namespaces.

See: https://issues.redhat.com/browse/AAH-1303

"""
import pytest
from ansible.errors import AnsibleError

from ..utils import (
    build_collection as galaxy_build_collection,
    get_all_namespaces,
    get_client,
    generate_unused_namespace,
    wait_for_all_tasks,
    wait_for_task,
)


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
@pytest.mark.min_hub_version("4.9dev")
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


def _test_namespace_logo_propagates_to_collections(ansible_config, upload_artifact, is_insights):
    admin_config = ansible_config("admin")
    api_prefix = admin_config.get("api_prefix").rstrip("/")
    api_client = get_client(admin_config, request_token=True, require_auth=True)

    namespace_name = generate_unused_namespace(api_client=api_client)

    # create empty namespace
    payload = {
        'name': namespace_name
    }
    my_namespace = api_client(f'{api_prefix}/_ui/v1/my-namespaces/', args=payload, method='POST')
    wait_for_all_tasks(api_client)
    assert my_namespace["avatar_url"] == ''
    assert my_namespace["avatar_sha256"] is None
    assert my_namespace["metadata_sha256"] is not None

    artifact = galaxy_build_collection(namespace=namespace_name)

    # upload collection to namespace
    upload_task = upload_artifact(admin_config, api_client, artifact)
    resp = wait_for_task(api_client, upload_task)
    assert resp["state"] == "completed"

    # verify cv index is correct
    search_url = (
        api_prefix
        + '/v3/plugin/ansible/search/collection-versions/'
        + f'?namespace={namespace_name}&name={artifact.name}'
    )
    resp = api_client.request(search_url)
    assert resp['data'][0]['namespace_metadata']["avatar_url"] is None

    # upload logo to namespace
    payload = {
        "name": namespace_name,
        "avatar_url": "http://placekitten.com/123/456"
    }
    api_client(f'{api_prefix}/_ui/v1/my-namespaces/{namespace_name}/', args=payload, method='PUT')
    wait_for_all_tasks(api_client)

    # namespace logo was updated correctly
    my_namespace = api_client(f'{api_prefix}/_ui/v1/my-namespaces/{namespace_name}/')
    assert my_namespace["avatar_url"] is not None

    search_url = (
        api_prefix
        + '/v3/plugin/ansible/search/collection-versions/'
        + f'?namespace={namespace_name}&name={artifact.name}'
    )
    resp = api_client(search_url)
    cv_namespace_metadata = resp['data'][0]['namespace_metadata']

    namespace_metadata = api_client(
        api_prefix
        + '/pulp/api/v3/content/ansible/namespaces/'
        f'?name={namespace_name}&ordering=-pulp_created'
    )['results'][0]

    # verify that collection is using latest namespace avatar
    assert cv_namespace_metadata['avatar_url'] == namespace_metadata['avatar_url']

    # in insights mode, avatar_url is stored in '_avatar_url' field
    # and is not hosted in the system, therefore it's different
    if is_insights is False:
        assert cv_namespace_metadata["avatar_url"] == my_namespace["avatar_url"]

    assert my_namespace["avatar_sha256"] is not None
    assert my_namespace["metadata_sha256"] is not None

    # update namespace
    payload = {
        "name": namespace_name,
        "description": "hehe hihi haha",
        "company": "RedHat Inc.",
        "avatar_url": "http://placekitten.com/654/321"
    }
    api_client(
        f'{api_prefix}/_ui/v1/my-namespaces/{namespace_name}/',
        args=payload,
        method='PUT'
    )
    assert my_namespace["avatar_sha256"] is not None
    assert my_namespace["metadata_sha256"] is not None
    wait_for_all_tasks(api_client)

    my_namespace = api_client(f'{api_prefix}/_ui/v1/my-namespaces/{namespace_name}/')

    # verify cv metadata are latest and correct
    search_url = (
        api_prefix
        + '/v3/plugin/ansible/search/collection-versions/'
        + f'?namespace={namespace_name}&name={artifact.name}'
    )
    resp = api_client(search_url)
    cv_namespace_metadata = resp['data'][0]['namespace_metadata']
    assert cv_namespace_metadata["description"] == "hehe hihi haha"
    assert cv_namespace_metadata["company"] == "RedHat Inc."

    namespace_metadata = api_client(
        api_prefix
        + '/pulp/api/v3/content/ansible/namespaces/'
        f'?name={namespace_name}&ordering=-pulp_created'
    )['results'][0]

    # verify cv idnex is using latest matedata
    assert cv_namespace_metadata['avatar_url'] == namespace_metadata['avatar_url']

    if is_insights is False:
        assert cv_namespace_metadata["avatar_url"] == my_namespace["avatar_url"]


@pytest.mark.namespace
@pytest.mark.deployment_community
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.9dev")
def test_namespace_logo_propagates_to_collections(ansible_config, upload_artifact):
    _test_namespace_logo_propagates_to_collections(ansible_config, upload_artifact, False)


@pytest.mark.namespace
@pytest.mark.deployment_cloud
def test_insights_namespace_logo_propagates_to_collections(ansible_config, upload_artifact):
    _test_namespace_logo_propagates_to_collections(ansible_config, upload_artifact, True)
