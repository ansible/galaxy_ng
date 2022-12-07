from ..utils import wait_for_task, cleanup_namespace, iterate_all


def set_synclist(api_client, collections):
    """Set the list of collections on the user's synclist and return the synclist object"""
    r = api_client("_ui/v1/my-synclists/")
    synclist_id = r["data"][0]["id"]
    synclist = api_client(f"_ui/v1/my-synclists/{synclist_id}/")

    synclist["collections"] = collections
    api_client(f"_ui/v1/my-synclists/{synclist_id}/", method="PUT", args=synclist)

    return r["data"][0]


def clear_certified(api_client):
    """Clear the content in the certified repo"""
    namespaces = set([
        c["namespace"] for c in iterate_all(
            api_client,
            "v3/plugin/ansible/content/rh-certified/collections/index/"
        )
    ])

    # We're deleting all the namespaces that correspond to collections in the
    # certified repo, because the tests need to verify that the namespaces are
    # created during sync.
    for ns in namespaces:
        cleanup_namespace(ns, api_client)


def perform_sync(api_client, crc_config, repo=None, remote_params=None):
    """Perform a sync against the crc_client defined by crc_config. """
    remote_params = remote_params or {}
    url = crc_config["url"]
    if repo:
        url = url + f"/content/{repo}/"

    # pulp_ansible will only perform a sync if the remote source is updated
    # or if the remote itself is modified. Since the remote source doesn't
    # change in the tests, force the remote to update bu setting the data
    # to dummy values before updating it.
    api_client(
        "content/rh-certified/v3/sync/config/",
        method="PUT",
        args={
            "url": "http://example.com/",
            "auth_url": "http://example.com/",
            "token": "foo",
            **remote_params,
        }
    )

    api_client(
        "content/rh-certified/v3/sync/config/",
        method="PUT",
        args={
            "url": url,
            "auth_url": crc_config["auth_url"],
            "token": crc_config["token"],
            **remote_params,
        }
    )

    # Launch sync
    r = api_client(
        "content/rh-certified/v3/sync/",
        method="POST"
    )

    resp = {
        "task": "pulp/api/v3/tasks/" + r["task"]
    }

    wait_for_task(api_client, resp)
