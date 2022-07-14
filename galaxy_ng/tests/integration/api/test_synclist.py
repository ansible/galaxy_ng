"""test_synclist.py - Test related to synclists."""

import pytest
from orionutils.generator import build_collection

from ..constants import USERNAME_PUBLISHER
from ..utils import get_client, set_certification, wait_for_task

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.galaxyapi_smoke
@pytest.mark.synclist
@pytest.mark.cloud_only
def test_synclist_object_get(ansible_config):
    """Validate user can read the endpoints with synclist objects."""

    config = ansible_config("org_admin")
    api_client = get_client(config, request_token=True, require_auth=True)

    resp = api_client("_ui/v1/my-synclists/", args={}, method="GET")
    assert resp["meta"]["count"] == 1
    print(f"resp={resp}")

    resp = api_client("_ui/v1/synclists/", args={}, method="GET")
    assert resp["meta"]["count"] > 0


@pytest.mark.galaxyapi_smoke
@pytest.mark.synclist
@pytest.mark.cloud_only
def test_synclist_object_edit(ansible_config, upload_artifact):
    """Edit the synclist json object and confirm data is saved.

    Note: the synclist object is not updated by adding one or removing one
    object like a collection, the json object needs to be updated to its
    future state before sending the PUT, and the synclist is overwritten.
    """

    # {
    #     'id': 2,
    #     'name': '6089720-synclist',
    #     'policy': 'exclude',
    #     'upstream_repository': '8b7f16b8-9753-4389-b6f6-32d5a8cbe247',
    #     'repository': 'b5dcd5b4-787b-4c59-84aa-96e87adc2014',
    #     'collections': [],
    #     'namespaces': [],
    #     'groups': [
    #         {
    #             'id': 2,
    #             'name': 'rh-identity-account:6089720',
    #             'object_permissions': [
    #                 'view_synclist', 'add_synclist', 'delete_synclist', 'change_synclist'
    #             ]
    #         }
    #     ]
    # }

    config = ansible_config("org_admin")
    api_client = get_client(config, request_token=True, require_auth=True)

    # determine synclist repo associated to user
    resp = api_client("_ui/v1/my-synclists/", args={}, method="GET")
    synclist_data_before = resp["data"][0]
    synclist_id = synclist_data_before["id"]

    # edit synclist payload
    my_synclist_url = f"_ui/v1/my-synclists/{synclist_id}/"
    synclist_data_after = dict(synclist_data_before)
    synclist_data_after["namespaces"] = [USERNAME_PUBLISHER]
    resp = api_client(my_synclist_url, args=synclist_data_after, method="PUT")

    # confirm synclist GET payload is same as payload sent via PUT
    resp = api_client(my_synclist_url, args={}, method="GET")
    assert resp == synclist_data_after

    # return synclist to previous state
    api_client(my_synclist_url, args=synclist_data_before, method="PUT")
    resp = api_client(my_synclist_url, args={}, method="GET")
    assert resp == synclist_data_before


@pytest.mark.galaxyapi_smoke
@pytest.mark.synclist
@pytest.mark.cloud_only
def test_edit_synclist_see_in_excludes(ansible_config, upload_artifact):
    """Edit SyncList object to exclude a collection,
    confirm see in content/{SyncList.name}/v3/excludes/
    confirm no change to content/{SyncList.name}/v3/collections/
    """

    # NOTE: on stage env, a toggle action does:
    # PUT https://console.stage.redhat.com/api/automation-hub/_ui/v1/my-synclists/1/

    config = ansible_config("partner_engineer")
    api_client = get_client(config, request_token=True, require_auth=True)

    def paginated_query(client, next_url, key="data"):
        """Iterate through a paginated url and dump all results into data"""
        resp = None
        while next_url:
            _resp = client(next_url)
            if resp is None:
                resp = _resp
            elif _resp[key]:
                resp[key].extend(_resp[key])
            next_url = _resp.get('links', {}).get('next')
        return resp

    # create and certify a new collection
    collection = build_collection("skeleton", config={"namespace": USERNAME_PUBLISHER})
    resp = upload_artifact(config, api_client, collection)
    resp = wait_for_task(api_client, resp)
    set_certification(api_client, collection)
    collection_key = (collection.namespace, collection.name)

    config = ansible_config("org_admin")
    api_client = get_client(config, request_token=True, require_auth=True)

    # determine synclist repo associated to user
    resp = api_client("_ui/v1/my-synclists/", args={}, method="GET")
    synclist_data_before = resp["data"][0]
    synclist_name = synclist_data_before["name"]
    synclist_id = synclist_data_before["id"]

    # check collection in viewset {synclist_name}/v3/collections/
    url = f"content/{synclist_name}/v3/collections/?limit=30"
    resp = paginated_query(api_client, url, key="data")
    collections_before = [(c["namespace"], c["name"]) for c in resp["data"]]
    assert collection_key in collections_before

    # check collection not in viewset {synclist_name}/v3/excludes/
    url = f"content/{synclist_name}/v3/excludes/"
    resp = paginated_query(api_client, url, key="collections")
    excludes = [(c["name"].split(".")[0], c["name"].split(".")[1]) for c in resp["collections"]]
    assert collection_key not in excludes

    # edit SyncList.collections
    my_synclist_url = f"_ui/v1/my-synclists/{synclist_id}/"
    synclist_data_after = dict(synclist_data_before)
    synclist_data_after["collections"] = [
        {"namespace": collection.namespace, "name": collection.name}
    ]
    resp = api_client(my_synclist_url, args=synclist_data_after, method="PUT")

    # check collection in viewset {synclist_name}/v3/excludes/
    url = f"content/{synclist_name}/v3/excludes/"
    resp = paginated_query(api_client, url, key="collections")
    excludes = [(c["name"].split(".")[0], c["name"].split(".")[1]) for c in resp["collections"]]
    assert collection_key in excludes

    # check viewset {synclist_name}/v3/collections/ has not changed
    url = f"content/{synclist_name}/v3/collections/?limit=30"
    resp = paginated_query(api_client, url, key="data")
    collections_after = [(c["namespace"], c["name"]) for c in resp["data"]]
    assert collections_before == collections_after
