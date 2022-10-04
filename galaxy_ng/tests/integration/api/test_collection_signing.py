"""Tests related to collection signing.

See: https://issues.redhat.com/browse/AAH-312
"""

import logging
import os
import tarfile
import time
from tempfile import TemporaryDirectory

import pytest
import requests
from orionutils.generator import build_collection

from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_ONETIME
from galaxy_ng.tests.integration.utils import (
    get_all_collections_by_repo,
    get_all_namespaces,
    get_client,
    set_certification,
    wait_for_task,
)

log = logging.getLogger(__name__)

NAMESPACE = "signing"


@pytest.fixture(scope="function")
def config(ansible_config):
    # FIXME: have this run partner_engineer profile
    return ansible_config("admin")


@pytest.fixture(scope="function")
def api_client(config):
    return get_client(config=config, request_token=True, require_auth=True)


@pytest.fixture(scope="function")
def settings(api_client):
    return api_client("/api/automation-hub/_ui/v1/settings/")


@pytest.fixture(scope="function")
def flags(api_client):
    return api_client("/api/automation-hub/_ui/v1/feature-flags/")


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
    resp = wait_for_task(api_client, resp)
    assert resp["state"] == "completed"
    return resp


def sign_on_demand(api_client, signing_service, sign_url=None, **payload):
    """Sign a collection on demand calling /sign/collections/"""
    sign_url = sign_url or "/api/automation-hub/_ui/v1/collection_signing/"
    sign_payload = {"signing_service": signing_service, **payload}
    resp = api_client(sign_url, method="POST", args=sign_payload)
    log.info("Sign Task: %s", resp)
    # FIXME - pulp tasks do not seem to accept token auth, so no way to check task progress
    time.sleep(SLEEP_SECONDS_ONETIME)
    return resp


@pytest.mark.collection_signing
@pytest.mark.collection_move
@pytest.mark.standalone_only
def test_collection_auto_sign_on_approval(api_client, config, settings, flags, upload_artifact):
    """Test whether a collection is uploaded and automatically signed on approval
    when GALAXY_AUTO_SIGN_COLLECTIONS is set to true.
    """
    if not flags.get("collection_auto_sign"):
        pytest.skip("GALAXY_AUTO_SIGN_COLLECTIONS is not enabled")
    else:
        log.info("GALAXY_AUTO_SIGN_COLLECTIONS is enabled")

    can_sign = flags.get("can_create_signatures")
    if not can_sign:
        pytest.skip("GALAXY_COLLECTION_SIGNING_SERVICE is not configured")

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

    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")

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
def test_collection_sign_on_demand(api_client, config, settings, flags, upload_artifact, sign_url):
    """Test whether a collection can be signed on-demand by calling _ui/v1/collection_signing/"""
    if not settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        pytest.skip(
            "GALAXY_REQUIRE_CONTENT_APPROVAL is False, "
            "so content is automatically signed during approval"
        )

    can_sign = flags.get("can_create_signatures")
    if not can_sign:
        pytest.skip("GALAXY_COLLECTION_SIGNING_SERVICE is not configured")

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

    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")

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
    metadata = collection_on_ui["latest_version"]["metadata"]
    assert len(metadata["signatures"]) >= 1
    assert metadata["signatures"][0]["signing_service"] == signing_service
    assert metadata["signatures"][0]["signature"] is not None
    assert metadata["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert metadata["signatures"][0]["pubkey_fingerprint"] is not None

    # Assert that the collection is signed on UI API (detail )
    collection_on_ui = api_client(
        f"/api/automation-hub/_ui/v1/repo/staging/{NAMESPACE}/{artifact.name}"
        f"/?version={artifact.version}"
    )
    assert collection_on_ui["sign_state"] == "signed"
    metadata = collection_on_ui["latest_version"]["metadata"]
    assert len(metadata["signatures"]) >= 1
    assert metadata["signatures"][0]["signing_service"] == signing_service
    assert metadata["signatures"][0]["signature"] is not None
    assert metadata["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert metadata["signatures"][0]["pubkey_fingerprint"] is not None


@pytest.mark.collection_signing
@pytest.mark.collection_move
@pytest.mark.standalone_only
def test_collection_move_with_signatures(api_client, config, settings, flags, upload_artifact):
    """Test whether a collection can be moved from repo to repo with its
    signatures.
    """
    can_sign = flags.get("can_create_signatures")
    if not can_sign:
        pytest.skip("GALAXY_COLLECTION_SIGNING_SERVICE is not configured")

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

    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")

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

    # # Assert that the collection is signed on UI API
    collection_on_ui = api_client(
        "/api/automation-hub/_ui/v1/repo/published/"
        f"?deprecated=false&namespace={NAMESPACE}&name={artifact.name}"
        f"&sign_state=signed&version={artifact.version}"
    )["data"][0]
    assert collection_on_ui["sign_state"] == "signed"
    metadata = collection_on_ui["latest_version"]["metadata"]
    assert len(metadata["signatures"]) >= 1
    assert metadata["signatures"][0]["signing_service"] == signing_service
    assert metadata["signatures"][0]["signature"] is not None
    assert metadata["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert metadata["signatures"][0]["pubkey_fingerprint"] is not None


@pytest.mark.collection_signing
@pytest.mark.collection_move
@pytest.mark.standalone_only  # This test can't run on cloud yet
def test_upload_signature(api_client, config, settings, upload_artifact):
    """
    1. If staging repository doesn't have a gpgkey, skip test
    2. Generate a collection
    3. Upload collection to staging
    4. Sign the collection MANIFEST.json file
    5. Upload the signature to staging
    6. assert collection signature task has spawned
    """
    if not settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_CONTENT_APPROVAL is not set")

    distributions = api_client("/api/automation-hub/_ui/v1/distributions/")
    if not distributions:
        pytest.skip("No distribution found")

    staging_has_gpgkey = False
    for distribution in distributions["data"]:
        if distribution["name"] == "staging":
            if distribution["repository"]["gpgkey"]:
                staging_has_gpgkey = True
                break

    if not staging_has_gpgkey:
        pytest.skip("Staging repository doesn't have a gpgkey")

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

    # extract all the contents of tarball to a temporary directory
    tarball = artifact.filename
    with TemporaryDirectory() as tmpdir:
        with tarfile.open(tarball, "r:gz") as tar:
            tar.extractall(tmpdir)
        manifest_file = os.path.join(tmpdir, "MANIFEST.json")
        signature_filename = f"{manifest_file}.asc"
        os.system(
            "gpg --batch --no-default-keyring --keyring test.kbx "
            "--import dev/common/ansible-sign.key"
        )
        os.system(f"KEYRING=test.kbx dev/common/collection_sign.sh {manifest_file}")

        if not os.path.exists(signature_filename):
            pytest.skip("Signature cannot be created")

        baseurl = config.get('url').rstrip('/') + '/' + 'pulp/api/v3/'

        collection_version_pk = collections["staging"][ckey]["id"]
        staging_resp = requests.get(
            baseurl + "repositories/ansible/ansible/?name=staging",
            auth=("admin", "admin"),
        )
        repo_href = staging_resp.json()["results"][0]["pulp_href"]
        signature_file = open(signature_filename, "rb")
        response = requests.post(
            baseurl + "content/ansible/collection_signatures/",
            files={"file": signature_file},
            data={
                "repository": repo_href,
                "signed_collection": (
                    "/api/automation-hub/pulp/api/v3/"
                    f"content/ansible/collection_versions/{collection_version_pk}/"
                ),
            },
            auth=("admin", "admin"),
        )
        assert "task" in response.json()

    time.sleep(SLEEP_SECONDS_ONETIME)  # wait for the task to finish

    # Assert that the collection is signed on v3 api
    collection = api_client(
        "/api/automation-hub/content/staging/v3/collections/"
        f"{artifact.namespace}/{artifact.name}/versions/{artifact.version}/"
    )
    assert len(collection["signatures"]) >= 1
    assert collection["signatures"][0]["signing_service"] is None
