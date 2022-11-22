import pytest

from ..utils import get_client, clear_certified, perform_sync, iterate_all, set_synclist


def _assert_sync(manifest, client):
    """
    Compares a manifest of expected collections with the state of the current system.

    Ensures that:
    - namespaces are created correctly
    - all the selected collections are available on
        - v3/
        - _ui/v1/repo/
    - all the selected collection versions are available on
        - _ui/v1/collection-versions/
    - deprecated content types are synced correctly
    - signatures are synced correctly
    - collection metadata is synced correctly 
    """

    namespaces = set()
    collections = set()
    versions = set()
    deprecated_collections = set()
    signed_collections = set()
    signed_versions = set()
    signatures = {}
    content = {}

    for cv in manifest:
        ns = cv["namespace"]
        collection = (ns, cv["name"])
        version = collection + (cv["version"], )

        namespaces.add(ns)
        versions.add(version)
        collections.add(collection)
        content[version] = cv["content_count"]

        if cv["is_signed"]:
            signed_collections.add(collection)
            signed_versions.add(version)
            signatures[version] = cv["signatures"]

        if cv["is_deprecated"]:
            deprecated_collections.add(collection)

    # test that all the expected namespaces are created
    all_namespaces = set([x["name"] for x in iterate_all(client, "v3/namespaces/")])
    assert namespaces.issubset(all_namespaces)

    # test that all the synced collections are on the v3 API
    synced_collections = set([(x["namespace"], x["name"]) for x in iterate_all(
        client,
        "v3/plugin/ansible/content/rh-certified/collections/index/"
    )])
    assert synced_collections == collections

    # Test that the _ui/v1/repo/ api returns all the synced collections
    synced_collections = set([(x["namespace"]["name"], x["name"]) for x in iterate_all(
        client,
        "_ui/v1/repo/rh-certified/"
    )])
    assert synced_collections == collections

    # Test that the _ui/v1/repo/ api returns all the synced collections
    synced_collections = set([(x["namespace"]["name"], x["name"]) for x in iterate_all(
        client,
        "_ui/v1/repo/rh-certified/?sign_state=signed"
    )])
    assert synced_collections == signed_collections

    # Test that the deprecated status syncs correctly
    synced_collections = set([(x["namespace"]["name"], x["name"]) for x in iterate_all(
        client,
        "_ui/v1/repo/rh-certified/?deprecated=false"
    )])
    assert synced_collections == collections.difference(deprecated_collections)

    # Test that the _ui/v1/collection-versions/ API shows the correct collections
    synced_versions = set()
    for c in iterate_all(
        client,
        "_ui/v1/collection-versions/?repository=rh-certified"
    ):
        version = (c["namespace"], c["name"], c["version"])
        synced_versions.add(version)
        assert len(c["contents"]) == content[version]

        if version in signed_versions:
            assert c["sign_state"] == "signed"
            local_sigs = set([x["signature"] for x in c["metadata"]["signatures"]])
            manifest_sigs = set([x["signature"] for x in signatures[version]])
            assert local_sigs == manifest_sigs
        else:
            assert c["sign_state"] == "unsigned"
            assert len(c["metadata"]["signatures"]) == 0

    assert synced_versions == versions


@pytest.mark.standalone_only
@pytest.mark.certified_sync
def test_basic_sync(sync_instance_crc, ansible_config):
    """Test syncing directly from the published repo."""

    config = ansible_config(profile="admin")
    manifest, crc_config = sync_instance_crc

    pah_client = get_client(
        config=config
    )

    clear_certified(pah_client)
    perform_sync(pah_client, crc_config)

    _assert_sync(manifest, pah_client)


@pytest.mark.standalone_only
@pytest.mark.certified_sync
def test_synclist_sync(sync_instance_crc, ansible_config):
    """Test syncing from a customer's synclist repo."""

    config = ansible_config(profile="admin")
    manifest, crc_config = sync_instance_crc

    pah_client = get_client(
        config=config
    )

    crc_client = get_client(
        config=crc_config,
        request_token=True,
        require_auth=True
    )

    clear_certified(pah_client)

    synclist_collection = manifest[0]
    synclist_manifest = manifest[1:]

    # Test exclude single collection
    repo = set_synclist(
        crc_client,
        [{
            "namespace": synclist_collection["namespace"],
            "name": synclist_collection["name"],
        }, ]
    )["name"]

    perform_sync(pah_client, crc_config, repo=repo)
    _assert_sync(synclist_manifest, pah_client)

    # update synclist
    repo = set_synclist(crc_client, [])["name"]

    perform_sync(pah_client, crc_config, repo=repo)
    _assert_sync(manifest, pah_client)


@pytest.mark.standalone_only
@pytest.mark.certified_sync
def test_signed_only_sync(sync_instance_crc, ansible_config):
    """Test syncing only signed collections."""

    config = ansible_config(profile="admin")
    manifest, crc_config = sync_instance_crc

    expected_manifest = [x for x in manifest if x["is_signed"]]

    pah_client = get_client(
        config=config
    )

    clear_certified(pah_client)

    perform_sync(pah_client, crc_config, remote_params={"signed_only": True})
    _assert_sync(expected_manifest, pah_client)
