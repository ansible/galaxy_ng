import pytest
import requests
import hashlib

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

    # Test that the _ui/v1/repo/ api returns all the synced signed collections
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


def _assert_namespace_sync(pah_client, crc_client, namespace):
    crc_ns = crc_client(f"v3/namespaces/{namespace['name']}/")
    pah_ns = pah_client(f"v3/plugin/ansible/content/rh-certified/namespaces/{namespace['name']}")
    pah_galaxy_ns = pah_client(f"v3/namespaces/{namespace['name']}/")

    # test the fields
    for field in ("metadata_sha256", "links", "email", "description", "resources", "company"):
        assert crc_ns[field] == pah_ns[field]
        assert crc_ns[field] == pah_galaxy_ns[field]

    # the url on the local namespace should be different from the remote
    assert crc_ns["avatar_url"] != pah_ns["avatar_url"]

    # test that the image downloaded correctly
    crc_avatar = requests.get(crc_ns["avatar_url"], allow_redirects=True).content
    pah_avatar = requests.get(pah_ns["avatar_url"], allow_redirects=True).content

    crc_sha = hashlib.sha256(crc_avatar).hexdigest()
    pah_sha = hashlib.sha256(pah_avatar).hexdigest()

    assert crc_sha == pah_sha
    assert pah_sha == pah_ns["avatar_sha256"]


@pytest.mark.sync
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


@pytest.mark.sync
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


@pytest.mark.sync
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


# @pytest.mark.skip("broken by python 3.11 ... ?")
@pytest.mark.sync
def test_namespace_sync(sync_instance_crc, ansible_config):
    pah_config = ansible_config(profile="admin")
    manifest, crc_config = sync_instance_crc

    crc_config.profile = "admin"

    pah_client = get_client(pah_config)
    crc_client = get_client(crc_config)

    ns_data = {
        "name": "ansible",
        "company": "Red Hat",
        "avatar_url": "https://avatars.githubusercontent.com/u/2103606",
        "groups": [],
        "links": [
            {"name": "link1", "url": "http://example.com"},
            {"name": "linkmaster 2", "url": "http://example.com/example"},
        ],
        "email": "hello@world.com",
        "description": (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Etiam tempus "
            "at urna eu auctor. Suspendisse potenti. Curabitur fringilla aliquam sem"
            " ac aliquet. Quisque porta augue id velit euismod, elementum vehicula "
            "neque volutpat."
        ),
        "resources": (
            "# Hello World\n"
            " Lorem ipsum dolor sit amet, consectetur adipiscing elit. Etiam tempus "
            "at urna eu auctor. Suspendisse potenti. Curabitur fringilla aliquam sem"
            " ac aliquet. Quisque porta augue id velit euismod, elementum vehicula "
            "neque volutpat. Donec ac urna at purus commodo laoreet. Nulla egestas "
            "imperdiet tincidunt. Morbi consequat egestas est accumsan eleifend. "
            "Pellentesque cursus interdum metus, eget consequat sapien convallis "
            "vitae. Integer sit amet aliquet turpis. Etiam risus lacus, viverra "
            "quis velit et, efficitur aliquam enim. Vivamus eu turpis et diam "
            "ultrices mollis.\n\n"
            "Mauris finibus tortor eget condimentum mollis. Etiam non ipsum ut "
            "metus venenatis faucibus. Ut tempor lacus sed ipsum fermentum maximus. "
            "Nunc fringilla rhoncus turpis eget placerat. Integer scelerisque pretium"
            " porttitor. Etiam quis vulputate mauris. Ut ultrices nisl a aliquet "
            "convallis. Nam bibendum purus tortor, et lacinia eros maximus a. Quisque "
            "euismod sapien nunc, in auctor eros blandit id. Proin pretium hendrerit "
            "augue, non sagittis dolor rhoncus a. Nullam vel est vel neque scelerisque"
            " condimentum. Integer efficitur ex eu augue laoreet, ut volutpat velit "
            "volutpat. Morbi id arcu sed dolor tincidunt pulvinar ac sed sem. Mauris "
            "posuere neque velit.\n\n"
            "Curabitur ultricies odio leo, hendrerit interdum felis semper ut. Aliquam"
            " eleifend leo quis ante faucibus tincidunt. In porttitor, quam nec molestie"
            " convallis, tortor ante ultricies arcu, et semper ligula sem quis enim. "
            "Nullam eleifend eros vitae mi luctus, in pellentesque nibh consequat. "
            "Curabitur magna risus, dignissim a convallis non, semper eu enim. "
            "Suspendisse vulputate sapien diam, in semper nulla fermentum at. Ut "
            "interdum sollicitudin suscipit. Etiam tempus ultrices ante, at sodales "
            "eros blandit vitae. Nulla facilisi. Nullam id vulputate quam, vel sagittis "
            "tortor. Vestibulum dolor mauris, lobortis sit amet justo rutrum, scelerisque "
            "iaculis purus. Pellentesque pharetra imperdiet erat, vitae vestibulum ipsum "
            "commodo eu. Donec tristique tortor tempor orci convallis finibus. Integer "
            "nec sagittis lectus. In ullamcorper laoreet nunc, quis mattis neque commodo "
            "in. Vestibulum eu risus sapien.\n\n"
        ),
    }

    ns = crc_client(
        "v3/namespaces/ansible/",
        args=ns_data,
        method="PUT",
    )

    clear_certified(pah_client)

    perform_sync(pah_client, crc_config)
    _assert_namespace_sync(pah_client, crc_client, ns)

    # update the namespace and sync again to verify that the new changes are
    # pulled down
    ns = crc_client(
        "v3/namespaces/ansible/",
        args={
            **ns_data,
            "description": "foo",
            "avatar_url": "https://avatars.githubusercontent.com/u/1507452"
        }
    )

    perform_sync(pah_client, crc_config)
    _assert_namespace_sync(pah_client, crc_client, ns)
