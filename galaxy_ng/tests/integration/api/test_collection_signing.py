"""Tests related to collection signing.

See: https://issues.redhat.com/browse/AAH-312
"""

import logging
import time
from urllib.parse import urljoin

import pytest
from orionutils.generator import build_collection

from ..utils import (
    get_all_collections_by_repo,
    get_all_namespaces,
    get_client,
    set_certification,
)

log = logging.getLogger(__name__)

NAMESPACE = "signing"


@pytest.fixture(scope="function")
def config(ansible_config):
    return ansible_config("ansible_partner")


@pytest.fixture(scope="function")
def api_client(config):
    return get_client(config=config, request_token=True, require_auth=True)


@pytest.fixture(scope="function")
def settings(api_client):
    return api_client("/api/automation-hub/_ui/v1/settings/")


@pytest.fixture(scope="function", autouse=True)
def namespace(api_client):
    # ensure namespace exists
    existing = dict((x["name"], x) for x in get_all_namespaces(api_client=api_client))
    if NAMESPACE not in existing:
        payload = {"name": NAMESPACE, "groups": []}
        api_client("/api/automation-hub/v3/namespaces/", args=payload, method="POST")
        return True  # created
    return False  # not created


def import_and_wait(api_client, artifact, upload_artifact, config):
    # import and wait ...
    resp = upload_artifact(config, api_client, artifact)
    ready = False
    url = urljoin(config["url"], resp["task"])
    log.info("Waiting for collection to be imported: %s", url)
    while not ready:
        resp = api_client(url)
        ready = resp["state"] not in ("running", "waiting")
        time.sleep(1)
    assert resp["state"] == "completed"
    return resp


def sign_on_demand(api_client, signing_service, sign_url=None, **payload):
    """Sign a collection on demand calling /sign/collections/"""
    sign_url = sign_url or "/api/automation-hub/_ui/v1/collection_signing/"
    sign_payload = {"signing_service": signing_service, **payload}
    resp = api_client(sign_url, method="POST", args=sign_payload)
    log.info("Sign Task: %s", resp)
    # FIXME - pulp tasks do not seem to accept token auth, so no way to check task progress
    time.sleep(3)
    return resp


@pytest.mark.collection_signing
@pytest.mark.collection_move
@pytest.mark.standalone_only
def test_collection_auto_sign_on_approval(api_client, config, settings, upload_artifact):
    """Test whether a collection is uploaded and automatically signed on approval
    when GALAXY_AUTO_SIGN_COLLECTIONS is set to true.
    """
    if not settings.get("GALAXY_AUTO_SIGN_COLLECTIONS"):
        pytest.skip("GALAXY_AUTO_SIGN_COLLECTIONS is not enabled")
    else:
        log.info("GALAXY_AUTO_SIGN_COLLECTIONS is enabled")

    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")
    if not signing_service:
        pytest.skip("GALAXY_SIGN_SERVICE is not set")

    artifact = build_collection(
        "skeleton",
        config={
            "namespace": NAMESPACE,
            "tags": ["tools"],
        },
    )
    ckey = (artifact.namespace, artifact.name, artifact.version)

    # import and wait ...
    import_and_wait(api_client, artifact, upload_artifact, config)

    if settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        # perform manual approval
        # Certify and check the response...
        cert_result = set_certification(api_client, artifact)
        assert cert_result["namespace"]["name"] == artifact.namespace
        assert cert_result["name"] == artifact.name
        assert cert_result["version"] == artifact.version
        assert cert_result["href"] is not None
        assert cert_result["metadata"]["tags"] == ["tools"]

    collections = get_all_collections_by_repo(api_client)
    assert ckey not in collections["staging"]
    assert ckey in collections["published"]

    # Assert that the collection is signed on v3 api
    collection = api_client(
        "/api/automation-hub/content/published/v3/collections/"
        f"{artifact.namespace}/{artifact.name}/versions/{artifact.version}/"
    )
    assert len(collection["signatures"]) >= 1
    assert collection["signatures"][0]["signing_service"] == signing_service
    assert collection["signatures"][0]["signature"] is not None
    assert collection["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert len(collection["signatures"][0]["signature"]) >= 256
    assert collection["signatures"][0]["pubkey_fingerprint"] is not None
    assert collection["signatures"][0]["pulp_created"] is not None

    # Assert that the collection is signed on UI API
    collection_on_ui = api_client(
        "/api/automation-hub/_ui/v1/repo/published/"
        f"?deprecated=false&namespace={NAMESPACE}&name={artifact.name}"
        f"&sign_state=signed&version={artifact.version}"
    )["data"][0]
    assert collection_on_ui["sign_state"] == "signed"
    assert collection_on_ui["total_versions"] == 1
    assert collection_on_ui["signed_versions"] == 1
    assert collection_on_ui["unsigned_versions"] == 0
    metadata = collection_on_ui["latest_version"]["metadata"]
    assert len(metadata["signatures"]) >= 1
    assert metadata["signatures"][0]["signing_service"] == signing_service
    assert metadata["signatures"][0]["signature"] is not None
    assert metadata["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert metadata["signatures"][0]["pubkey_fingerprint"] is not None


@pytest.mark.collection_signing
@pytest.mark.standalone_only
@pytest.mark.parametrize(
    "sign_url",
    [
        "/api/automation-hub/_ui/v1/collection_signing/",
        "/api/automation-hub/_ui/v1/collection_signing/{distro_base_path}/",
        "/api/automation-hub/_ui/v1/collection_signing/{distro_base_path}/{namespace}/",
        (
            "/api/automation-hub/_ui/v1/collection_signing/"
            "{distro_base_path}/{namespace}/{collection}/"
        ),
        (
            "/api/automation-hub/_ui/v1/collection_signing/"
            "{distro_base_path}/{namespace}/{collection}/{version}/"
        ),
    ],
)
def test_collection_sign_on_demand(api_client, config, settings, upload_artifact, sign_url):
    """Test whether a collection can be signed on-demand by calling _ui/v1/collection_signing/"""
    if not settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        pytest.skip(
            "GALAXY_REQUIRE_CONTENT_APPROVAL is False, "
            "so content is automatically signed during approval"
        )

    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")
    if not signing_service:
        pytest.skip("GALAXY_SIGN_SERVICE is not set")

    artifact = build_collection(
        "skeleton",
        config={
            "namespace": NAMESPACE,
            "tags": ["tools"],
        },
    )
    ckey = (artifact.namespace, artifact.name, artifact.version)

    # import and wait ...
    import_and_wait(api_client, artifact, upload_artifact, config)

    # Collection must be on /staging/
    collections = get_all_collections_by_repo(api_client)
    assert ckey in collections["staging"]
    assert ckey not in collections["published"]

    # Sign the collection
    sign_payload = {
        "distro_base_path": "staging",
        "namespace": NAMESPACE,
        "collection": artifact.name,
        "version": artifact.version,
    }
    sign_on_demand(api_client, signing_service, sign_url.format(**sign_payload), **sign_payload)

    # Assert that the collection is signed on v3 api
    collection = api_client(
        "/api/automation-hub/content/staging/v3/collections/"
        f"{artifact.namespace}/{artifact.name}/versions/{artifact.version}/"
    )
    assert len(collection["signatures"]) >= 1
    assert collection["signatures"][0]["signing_service"] == signing_service
    assert collection["signatures"][0]["signature"] is not None
    assert collection["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert len(collection["signatures"][0]["signature"]) >= 256
    assert collection["signatures"][0]["pubkey_fingerprint"] is not None
    assert collection["signatures"][0]["pulp_created"] is not None

    # Assert that the collection is signed on UI API
    collection_on_ui = api_client(
        "/api/automation-hub/_ui/v1/repo/staging/"
        f"?deprecated=false&namespace={NAMESPACE}&name={artifact.name}"
        f"&sign_state=signed&version={artifact.version}"
    )["data"][0]
    assert collection_on_ui["sign_state"] == "signed"
    assert collection_on_ui["total_versions"] == 1
    assert collection_on_ui["signed_versions"] == 1
    assert collection_on_ui["unsigned_versions"] == 0
    metadata = collection_on_ui["latest_version"]["metadata"]
    assert len(metadata["signatures"]) >= 1
    assert metadata["signatures"][0]["signing_service"] == signing_service
    assert metadata["signatures"][0]["signature"] is not None
    assert metadata["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert metadata["signatures"][0]["pubkey_fingerprint"] is not None


@pytest.mark.collection_signing
@pytest.mark.collection_move
@pytest.mark.standalone_only
def test_collection_move_with_signatures(api_client, config, settings, upload_artifact):
    """Test whether a collection can be moved from repo to repo with its
    signatures.
    """
    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")
    if not signing_service:
        pytest.skip("GALAXY_SIGN_SERVICE is not set")

    artifact = build_collection(
        "skeleton",
        config={
            "namespace": NAMESPACE,
            "tags": ["tools"],
        },
    )
    ckey = (artifact.namespace, artifact.name, artifact.version)

    # import and wait ...
    import_and_wait(api_client, artifact, upload_artifact, config)

    # Collection must be on /staging/
    collections = get_all_collections_by_repo(api_client)
    assert ckey in collections["staging"]
    assert ckey not in collections["published"]

    if settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        # Sign the collection while still on staging
        sign_payload = {
            "distro_base_path": "staging",
            "namespace": NAMESPACE,
            "collection": artifact.name,
            "version": artifact.version,
        }
        sign_on_demand(api_client, signing_service, **sign_payload)

        # Assert that the collection is signed on v3 api
        collection = api_client(
            "/api/automation-hub/content/staging/v3/collections/"
            f"{artifact.namespace}/{artifact.name}/versions/{artifact.version}/"
        )
        assert len(collection["signatures"]) >= 1
        assert collection["signatures"][0]["signing_service"] == signing_service

        # Assert that the collection is signed on UI API
        collections = get_all_collections_by_repo(api_client)
        assert collections["staging"][ckey]["sign_state"] == "signed"

        # Move the collection to /published/
        cert_result = set_certification(api_client, artifact)
        assert cert_result["namespace"]["name"] == artifact.namespace
        assert cert_result["name"] == artifact.name
        assert cert_result["version"] == artifact.version
        assert cert_result["href"] is not None
        assert cert_result["metadata"]["tags"] == ["tools"]
        assert len(cert_result["signatures"]) >= 1

    # After moving to /published/
    # Assert that the collection is signed on v3 api
    collection = api_client(
        "/api/automation-hub/content/published/v3/collections/"
        f"{artifact.namespace}/{artifact.name}/versions/{artifact.version}/"
    )
    assert len(collection["signatures"]) >= 1
    assert collection["signatures"][0]["signing_service"] == signing_service
    assert collection["signatures"][0]["signature"] is not None
    assert collection["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert len(collection["signatures"][0]["signature"]) >= 256
    assert collection["signatures"][0]["pubkey_fingerprint"] is not None
    assert collection["signatures"][0]["pulp_created"] is not None

    # Assert that the collection is signed on UI API
    collection_on_ui = api_client(
        "/api/automation-hub/_ui/v1/repo/published/"
        f"?deprecated=false&namespace={NAMESPACE}&name={artifact.name}"
        f"&sign_state=signed&version={artifact.version}"
    )["data"][0]
    assert collection_on_ui["sign_state"] == "signed"
    assert collection_on_ui["total_versions"] == 1
    assert collection_on_ui["signed_versions"] == 1
    assert collection_on_ui["unsigned_versions"] == 0
    metadata = collection_on_ui["latest_version"]["metadata"]
    assert len(metadata["signatures"]) >= 1
    assert metadata["signatures"][0]["signing_service"] == signing_service
    assert metadata["signatures"][0]["signature"] is not None
    assert metadata["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert metadata["signatures"][0]["pubkey_fingerprint"] is not None
