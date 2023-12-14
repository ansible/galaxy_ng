"""test_namespace_management.py - Test related to namespaces.

See: https://issues.redhat.com/browse/AAH-1303

"""
from time import sleep

import pytest

from galaxykit.namespaces import get_namespace, get_namespace_collections
from galaxykit.repositories import search_collection
from galaxykit.users import get_me

from ..utils.iqe_utils import is_stage_environment
from ..utils.repo_management_utils import upload_new_artifact
from ..utils.tasks import wait_for_all_tasks_gk, wait_for_namespace_tasks_gk
from ..utils.tools import generate_random_string

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
def test_namespace_create_and_delete(api_version, galaxy_client):
    """Tests whether a namespace can be created and deleted"""

    # http://192.168.1.119:8002/api/automation-hub/_ui/v1/namespaces/
    # http://192.168.1.119:8002/api/automation-hub/v3/namespaces/
    # {name: "testnamespace1", groups: []}
    gc = galaxy_client("partner_engineer")
    new_namespace = f"ns_test_{generate_random_string()}"
    payload = {'name': new_namespace, 'groups': []}
    resp = gc.post(f"{api_version}/namespaces/", body=payload)
    wait_for_namespace_tasks_gk(gc)
    assert resp['name'] == new_namespace
    if api_version == "v3":
        get_namespace(gc, new_namespace)
        gc.delete(f"{api_version}/namespaces/{new_namespace}/", parse_json=False)
        with pytest.raises(KeyError):
            get_namespace(gc, new_namespace)
    if api_version == "_ui/v1":
        gc.get(f"{api_version}/namespaces/?name={new_namespace}")
        gc.delete(f"{api_version}/namespaces/{new_namespace}/", parse_json=False)
        r = get_namespace_collections(gc, new_namespace)
        assert len(r["data"]) == 0


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
def test_namespace_create_with_user(galaxy_client, user_property):
    gc = galaxy_client("partner_engineer")
    me = get_me(gc)
    username = me['username']
    new_namespace = f"ns_test_{generate_random_string()}"
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
    resp = gc.post("_ui/v1/my-namespaces/", body=payload)

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
def test_namespace_edit_with_user(galaxy_client, user_property):
    gc = galaxy_client("partner_engineer")
    me = get_me(gc)
    username = me['username']

    new_namespace = f"ns_test_{generate_random_string()}"
    # make a namespace without users and without groups ...
    payload = {
        'name': new_namespace,
    }
    resp = gc.post("_ui/v1/my-namespaces/", body=payload)
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
    resp = gc.put(f"_ui/v1/my-namespaces/{new_namespace}/", body=payload)
    # should have the right results ...
    assert resp['name'] == new_namespace
    assert resp['groups'] == []
    assert resp['users'] != []
    assert username in [x['name'] for x in resp['users']]
    assert sorted(resp['users'][0]['object_roles']) == sorted(object_roles)


@pytest.mark.namespace
@pytest.mark.all
@pytest.mark.min_hub_version("4.9dev")
def test_namespace_edit_logo(galaxy_client):
    gc = galaxy_client("admin")
    new_namespace = f"ns_test_{generate_random_string()}"
    payload = {
        'name': new_namespace,
    }
    my_namespace = gc.post("_ui/v1/my-namespaces/", body=payload)
    assert my_namespace["avatar_url"] == ''

    namespaces = gc.get('_ui/v1/my-namespaces/')
    name = my_namespace["name"]

    payload = {
        "name": name,
        # "avatar_url": "http://placekitten.com/400/400"
        "avatar_url": "https://avatars.githubusercontent.com/u/1869705?v=4"
    }
    gc.put(f"_ui/v1/my-namespaces/{name}/", body=payload)
    wait_for_all_tasks_gk(gc)
    updated_namespace = gc.get(f'_ui/v1/my-namespaces/{name}/')
    assert updated_namespace["avatar_url"] != ""

    payload = {
        "name": name,
        # "avatar_url": "http://placekitten.com/123/456"
        "avatar_url": "https://avatars.githubusercontent.com/u/481677?v=4"
    }
    gc.put(f"_ui/v1/my-namespaces/{name}/", body=payload)
    wait_for_all_tasks_gk(gc)
    updated_again_namespace = gc.get(f"_ui/v1/my-namespaces/{name}/")
    assert updated_namespace["avatar_url"] != updated_again_namespace["avatar_url"]

    # verify no additional namespaces are created
    resp = gc.get("_ui/v1/my-namespaces/")
    assert resp["meta"]["count"] == namespaces["meta"]["count"]

    # verify no side effects
    # fields that should NOT change
    for field in ["pulp_href", "name", "company", "email", "description", "resources", "links"]:
        assert my_namespace[field] == updated_again_namespace[field]

    # fields that changed
    for field in ["avatar_url", "metadata_sha256", "avatar_sha256"]:
        assert my_namespace[field] != updated_again_namespace[field]


def _test_namespace_logo_propagates_to_collections(galaxy_client, is_insights):
    gc = galaxy_client("admin")
    namespace_name = f"ns_test_{generate_random_string()}"
    payload = {
        'name': namespace_name
    }
    my_namespace = gc.post("_ui/v1/my-namespaces/", body=payload)
    assert my_namespace["avatar_url"] == ''
    assert my_namespace["avatar_sha256"] is None
    assert my_namespace["metadata_sha256"] is not None

    artifact = upload_new_artifact(
        gc, namespace_name, "published", "1.0.1", tags=["application"]
    )
    if is_stage_environment():
        sleep(90)

    resp = search_collection(gc, namespace=namespace_name, name=artifact.name)

    assert resp['data'][0]['namespace_metadata']["avatar_url"] is None

    # upload logo to namespace
    payload = {
        "name": namespace_name,
        # "avatar_url": "http://placekitten.com/123/456"
        "avatar_url": "https://avatars.githubusercontent.com/u/1869705?v=4"
    }
    gc.put(f"_ui/v1/my-namespaces/{namespace_name}/", body=payload)
    if is_stage_environment():
        sleep(90)
    wait_for_all_tasks_gk(gc)

    # namespace logo was updated correctly
    my_namespace = gc.get(f'_ui/v1/my-namespaces/{namespace_name}/')
    assert my_namespace["avatar_url"] is not None

    resp = search_collection(gc, namespace=namespace_name, name=artifact.name)
    cv_namespace_metadata = resp['data'][0]['namespace_metadata']
    resp = gc.get(f"pulp/api/v3/content/ansible/namespaces/"
                  f"?name={namespace_name}&ordering=-pulp_created")
    namespace_metadata = resp['results'][0]
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
        # "avatar_url": "http://placekitten.com/654/321"
        "avatar_url": "https://avatars.githubusercontent.com/u/481677?v=4"
    }
    gc.put(f"_ui/v1/my-namespaces/{namespace_name}/", body=payload)
    if is_stage_environment():
        sleep(90)
    assert my_namespace["avatar_sha256"] is not None
    assert my_namespace["metadata_sha256"] is not None
    wait_for_all_tasks_gk(gc)

    my_namespace = gc.get(f'_ui/v1/my-namespaces/{namespace_name}/')

    # verify cv metadata are latest and correct
    resp = search_collection(gc, namespace=namespace_name, name=artifact.name)
    cv_namespace_metadata = resp['data'][0]['namespace_metadata']
    assert cv_namespace_metadata["description"] == "hehe hihi haha"
    assert cv_namespace_metadata["company"] == "RedHat Inc."

    resp = gc.get(f"pulp/api/v3/content/ansible/namespaces/"
                  f"?name={namespace_name}&ordering=-pulp_created")
    namespace_metadata = resp["results"][0]
    # verify cv idnex is using latest matedata
    assert cv_namespace_metadata['avatar_url'] == namespace_metadata['avatar_url']

    if is_insights is False:
        assert cv_namespace_metadata["avatar_url"] == my_namespace["avatar_url"]


@pytest.mark.namespace
@pytest.mark.deployment_community
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.9dev")
def test_namespace_logo_propagates_to_collections(galaxy_client):
    _test_namespace_logo_propagates_to_collections(galaxy_client, False)


@pytest.mark.namespace
@pytest.mark.deployment_cloud
def test_insights_namespace_logo_propagates_to_collections(galaxy_client):
    _test_namespace_logo_propagates_to_collections(galaxy_client, True)
