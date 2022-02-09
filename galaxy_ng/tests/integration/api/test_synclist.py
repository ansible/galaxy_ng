"""test_synclist.py - Test related to synclists."""

import os
import time
from contextlib import contextmanager

import pytest
from ansible.galaxy.api import GalaxyError
from orionutils.generator import build_collection

from ..constants import USERNAME_PUBLISHER
from ..utils import get_client, set_certification, wait_for_task

pytestmark = pytest.mark.qa  # noqa: F821


# TODO: see if ansible_config() does or can be made to accept a user param
@contextmanager
def set_username_env_var(hub_username):
    try:
        original_username = os.environ.get("HUB_USERNAME", "")
        os.environ["HUB_USERNAME"] = hub_username
        yield
    finally:
        os.environ["HUB_USERNAME"] = original_username


@pytest.mark.galaxyapi_smoke
@pytest.mark.synclist
@pytest.mark.cloud_only
def test_synclist_object_get(ansible_config):
    """Validate user can read the endpoints with synclist objects."""

    # set user to org-admin to access synclists
    with set_username_env_var("org-admin"):
        config = ansible_config("ansible_partner")
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

    # set user to org-admin to access synclists
    with set_username_env_var("org-admin"):
        config = ansible_config("ansible_partner")
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
def test_synclist_object_and_synclist_repo_edit(ansible_config, upload_artifact):
    """Edit synclist object to exclude a collection, do curate task,
    confirm collection removed from synclist repository."""

    # NOTE: on stage env, a toggle action accesses these:
    # PUT https://console.stage.redhat.com/api/automation-hub/_ui/v1/my-synclists/1/
    # POST https://console.stage.redhat.com/api/automation-hub/_ui/v1/my-synclists/1/curate/

    config = ansible_config("ansible_partner")
    api_client = get_client(config, request_token=True, require_auth=True)

    # create and certify a new collection
    collection = build_collection("skeleton", config={"namespace": USERNAME_PUBLISHER})
    resp = upload_artifact(config, api_client, collection)
    resp = wait_for_task(api_client, resp)
    set_certification(api_client, collection)
    collection_key = (collection.namespace, collection.name)

    # set user to org-admin to access synclists
    with set_username_env_var("org-admin"):
        config = ansible_config("ansible_partner")
        api_client = get_client(config, request_token=True, require_auth=True)

    # determine synclist repo associated to user
    resp = api_client("_ui/v1/my-synclists/", args={}, method="GET")
    synclist_data_before = resp["data"][0]
    synclist_name = synclist_data_before["name"]
    synclist_id = synclist_data_before["id"]

    # check that collection is part of synclist repo
    url = f"content/{synclist_name}/v3/collections/?limit=30"
    resp = api_client(url)
    collections_before = [(c["namespace"], c["name"]) for c in resp["data"]]
    assert collection_key in collections_before

    # edit synclist payload
    my_synclist_url = f"_ui/v1/my-synclists/{synclist_id}/"
    synclist_data_after = dict(synclist_data_before)
    synclist_data_after["collections"] = [
        {"namespace": collection.namespace, "name": collection.name}
    ]
    resp = api_client(my_synclist_url, args=synclist_data_after, method="PUT")

    # kick off a curate task
    resp = api_client(f"_ui/v1/my-synclists/{synclist_id}/curate/", args={}, method="POST")

    # wait for the curate task to finish
    try:
        wait_for_task(api_client, resp)
    except GalaxyError as ge:
        # FIXME - pulp tasks do not seem to accept token auth
        if ge.http_code in [403, 404]:
            time.sleep(5)
        else:
            raise Exception(ge)

    # check collection is NOT part of synclist repo
    url = f"content/{synclist_name}/v3/collections/?limit=30"
    resp = api_client(url)
    collections_after = [(c["namespace"], c["name"]) for c in resp["data"]]
    assert collection_key not in collections_after
