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
    build_collection as galaxy_build_collection,
    get_all_collections_by_repo,
    get_all_namespaces,
    set_certification,
    create_local_signature_for_tarball,
)
from galaxy_ng.tests.integration.utils.repo_management_utils import create_test_namespace
from galaxykit.collections import upload_artifact, get_collection_from_repo, get_ui_collection, \
    move_or_copy_collection
from galaxykit.distributions import get_v1_distributions
from galaxykit.repositories import get_repository_href, move_content_between_repos
from galaxykit.utils import wait_for_task, GalaxyClientError

log = logging.getLogger(__name__)

NAMESPACE = "signing"


@pytest.fixture(scope="function")
def flags(galaxy_client):
    gc = galaxy_client("admin")
    return gc.get("_ui/v1/feature-flags/")


@pytest.fixture(scope="function", autouse=True)
def namespace(galaxy_client):
    # ensure namespace exists
    gc = galaxy_client("admin")
    existing = dict((x["name"], x) for x in get_all_namespaces(gc))
    if NAMESPACE not in existing:
        payload = {"name": NAMESPACE, "groups": []}
        gc.post("v3/namespaces/", body=payload)
        return True  # created
    return False  # not created


def sign_on_demand(gc, signing_service, sign_url=None, **payload):
    """Sign a collection on demand calling /sign/collections/"""
    sign_url = sign_url or "_ui/v1/collection_signing/"
    sign_payload = {"signing_service": signing_service, **payload}

    '''
    # need to get the x-repo list now ...
    cvs = get_all_repository_collection_versions(api_client=api_client)
    import epdb; epdb.st()
    '''
    resp = gc.post(sign_url, body=sign_payload)
    log.info("Sign Task: %s", resp)
    # FIXME - pulp tasks do not seem to accept token auth, so no way to check task progress
    time.sleep(SLEEP_SECONDS_ONETIME)
    return resp


@pytest.mark.collection_signing
@pytest.mark.collection_move
@pytest.mark.deployment_standalone
def test_collection_auto_sign_on_approval(ansible_config, flags, galaxy_client, settings):
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
    gc = galaxy_client("admin")
    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)
    assert resp["state"] == "completed"

    if settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        # perform manual approval
        # Certify and check the response...
        gc = galaxy_client("partner_engineer")
        cert_result = set_certification(ansible_config(), gc, artifact)
        assert cert_result["namespace"]["name"] == artifact.namespace
        assert cert_result["name"] == artifact.name
        assert cert_result["version"] == artifact.version
        assert cert_result["href"] is not None
        assert cert_result["metadata"]["tags"] == ["tools"]

    collections = get_all_collections_by_repo(gc)
    assert ckey not in collections["staging"]
    assert ckey in collections["published"]

    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")

    # Assert that the collection is signed on v3 api
    collection = get_collection_from_repo(gc, "published",
                                          artifact.namespace, artifact.name, artifact.version)
    assert len(collection["signatures"]) >= 1
    assert collection["signatures"][0]["signing_service"] == signing_service
    assert collection["signatures"][0]["signature"] is not None
    assert collection["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert len(collection["signatures"][0]["signature"]) >= 256
    assert collection["signatures"][0]["pubkey_fingerprint"] is not None
    assert collection["signatures"][0]["pulp_created"] is not None

    # Assert that the collection is signed on UI API
    collection_on_ui = gc.get(f"_ui/v1/repo/published/"
                              f"?deprecated=false&namespace={NAMESPACE}&name={artifact.name}"
                              f"&sign_state=signed&version={artifact.version}")["data"][0]
    assert collection_on_ui["sign_state"] == "signed"
    metadata = collection_on_ui["latest_version"]["metadata"]
    assert len(metadata["signatures"]) >= 1
    assert metadata["signatures"][0]["signing_service"] == signing_service
    assert metadata["signatures"][0]["signature"] is not None
    assert metadata["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert metadata["signatures"][0]["pubkey_fingerprint"] is not None


@pytest.mark.collection_signing
@pytest.mark.deployment_standalone
@pytest.mark.parametrize(
    "sign_url",
    [
        "_ui/v1/collection_signing/",
        "_ui/v1/collection_signing/{distro_base_path}/",
        "_ui/v1/collection_signing/{distro_base_path}/{namespace}/",
        (
            "_ui/v1/collection_signing/"
            "{distro_base_path}/{namespace}/{collection}/"
        ),
        (
            "_ui/v1/collection_signing/"
            "{distro_base_path}/{namespace}/{collection}/{version}/"
        ),
    ],
)
def test_collection_sign_on_demand(flags, galaxy_client, settings, sign_url):
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
    gc = galaxy_client("admin")
    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)
    assert resp["state"] == "completed"

    # Collection must be on /staging/
    collections = get_all_collections_by_repo(gc)
    assert ckey in collections["staging"]
    assert ckey not in collections["published"]

    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")

    # Sign the collection
    sign_payload = {
        "api_prefix": gc.galaxy_root,
        "distro_base_path": "staging",
        "namespace": NAMESPACE,
        "collection": artifact.name,
        "version": artifact.version,
    }
    sign_on_demand(gc, signing_service, sign_url.format(**sign_payload), **sign_payload)
    # Assert that the collection is signed on v3 api
    collection = get_collection_from_repo(gc, "staging",
                                          artifact.namespace, artifact.name, artifact.version)
    assert len(collection["signatures"]) >= 1
    assert collection["signatures"][0]["signing_service"] == signing_service
    assert collection["signatures"][0]["signature"] is not None
    assert collection["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert len(collection["signatures"][0]["signature"]) >= 256
    assert collection["signatures"][0]["pubkey_fingerprint"] is not None
    assert collection["signatures"][0]["pulp_created"] is not None

    # Assert that the collection is signed on UI API
    collection_on_ui = gc.get(f"_ui/v1/repo/staging/?deprecated=false&namespace="
                              f"{NAMESPACE}&name={artifact.name}&sign_state=signed"
                              f"&version={artifact.version}")["data"][0]
    assert collection_on_ui["sign_state"] == "signed"
    metadata = collection_on_ui["latest_version"]["metadata"]
    assert len(metadata["signatures"]) >= 1
    assert metadata["signatures"][0]["signing_service"] == signing_service
    assert metadata["signatures"][0]["signature"] is not None
    assert metadata["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert metadata["signatures"][0]["pubkey_fingerprint"] is not None

    # Assert that the collection is signed on UI API (detail )
    collection_on_ui = get_ui_collection(gc, "staging",
                                         NAMESPACE, artifact.name, artifact.version)
    assert collection_on_ui["sign_state"] == "signed"
    metadata = collection_on_ui["latest_version"]["metadata"]
    assert len(metadata["signatures"]) >= 1
    assert metadata["signatures"][0]["signing_service"] == signing_service
    assert metadata["signatures"][0]["signature"] is not None
    assert metadata["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert metadata["signatures"][0]["pubkey_fingerprint"] is not None


@pytest.mark.collection_signing
@pytest.mark.collection_move
@pytest.mark.deployment_standalone
def test_collection_move_with_signatures(ansible_config, flags, galaxy_client, settings):
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
    gc = galaxy_client("admin")
    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)
    assert resp["state"] == "completed"

    # Collection must be on /staging/
    collections = get_all_collections_by_repo(gc)
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
        sign_on_demand(gc, signing_service, **sign_payload)

        # Assert that the collection is signed on v3 api
        collection = get_collection_from_repo(gc, "staging", artifact.namespace,
                                              artifact.name, artifact.version)
        assert len(collection["signatures"]) >= 1
        assert collection["signatures"][0]["signing_service"] == signing_service

        # Assert that the collection is signed on UI API
        collections = get_all_collections_by_repo(gc)
        assert collections["staging"][ckey]["sign_state"] == "signed"

        # Move the collection to /published/
        gc = galaxy_client("partner_engineer")
        cert_result = set_certification(ansible_config(), gc, artifact)
        assert cert_result["namespace"]["name"] == artifact.namespace
        assert cert_result["name"] == artifact.name
        assert cert_result["version"] == artifact.version
        assert cert_result["href"] is not None
        assert cert_result["metadata"]["tags"] == ["tools"]
        assert len(cert_result["signatures"]) >= 1

    # After moving to /published/
    # Assert that the collection is signed on v3 api
    collection = get_collection_from_repo(gc, "published", artifact.namespace,
                                          artifact.name, artifact.version)

    assert len(collection["signatures"]) >= 1
    assert collection["signatures"][0]["signing_service"] == signing_service
    assert collection["signatures"][0]["signature"] is not None
    assert collection["signatures"][0]["signature"].startswith("-----BEGIN PGP SIGNATURE-----")
    assert len(collection["signatures"][0]["signature"]) >= 256
    assert collection["signatures"][0]["pubkey_fingerprint"] is not None
    assert collection["signatures"][0]["pulp_created"] is not None

    # # Assert that the collection is signed on UI API
    collection_on_ui = gc.get(
        f"_ui/v1/repo/published/"
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
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_copy_collection_without_signatures(flags, galaxy_client, settings):
    """Test whether a collection can be added to a second repo without its signatures."""
    can_sign = flags.get("can_create_signatures")
    if not can_sign:
        pytest.skip("GALAXY_COLLECTION_SIGNING_SERVICE is not configured")

    if settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL") is not True:
        pytest.skip("Approval is automatically done")

    artifact = build_collection(
        "skeleton",
        config={
            "namespace": NAMESPACE,
            "tags": ["tools", "copytest"],
        },
    )
    ckey = (artifact.namespace, artifact.name, artifact.version)

    # import and wait ...
    gc = galaxy_client("admin")
    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)
    assert resp["state"] == "completed"

    # Collection must be on /staging/
    collections = get_all_collections_by_repo(gc)
    assert ckey in collections["staging"]

    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")

    # Sign the collection while still on staging
    sign_payload = {
        "distro_base_path": "staging",
        "namespace": NAMESPACE,
        "collection": artifact.name,
        "version": artifact.version,
    }
    sign_on_demand(gc, signing_service, **sign_payload)

    # Assert that the collection is signed on v3 api
    collection = get_collection_from_repo(gc, "staging", artifact.namespace,
                                          artifact.name, artifact.version)

    assert len(collection["signatures"]) >= 1
    assert collection["signatures"][0]["signing_service"] == signing_service

    copy_result = move_or_copy_collection(gc, artifact.namespace, artifact.name,
                                          artifact.version, source="staging",
                                          destination="community", operation="copy")

    assert copy_result["namespace"]["name"] == artifact.namespace
    assert copy_result["name"] == artifact.name
    assert copy_result["version"] == artifact.version
    assert copy_result["href"] is not None
    expected_tags = ["tools", "copytest"]
    actual_tags = copy_result["metadata"]["tags"]
    assert sorted(actual_tags) == sorted(expected_tags)
    assert len(copy_result["signatures"]) == 1

    # Assert that the collection is signed on ui/stating but not on ui/community
    collections = get_all_collections_by_repo(gc)
    assert collections["staging"][ckey]["sign_state"] == "signed"
    assert collections["community"][ckey]["sign_state"] == "signed"


@pytest.mark.collection_signing
@pytest.mark.collection_move
@pytest.mark.deployment_standalone  # This test can't run on cloud yet
@pytest.mark.parametrize(
    "require_auth",
    [
        True,
        False,
    ],
)
def test_upload_signature(require_auth, flags, galaxy_client, settings):
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

    gc = galaxy_client("admin")
    distributions = get_v1_distributions(gc)
    if not distributions:
        pytest.skip("No distribution found")

    staging_has_gpgkey = False
    for distribution in distributions["data"]:
        if distribution["name"] == "staging":
            try:
                if distribution["repository"]["gpgkey"]:
                    staging_has_gpgkey = True
                    break
            except KeyError:
                pass

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
    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)
    assert resp["state"] == "completed"    # Collection must be on /staging/
    collections = get_all_collections_by_repo(gc)
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

        collection_version_pk = collections["staging"][ckey]["id"]
        repo_href = get_repository_href(gc, "staging")
        signature_file = open(signature_filename, "rb")
        response = requests.post(
            gc.galaxy_root + "pulp/api/v3/content/ansible/collection_signatures/",
            verify=False,
            files={"file": signature_file},
            data={
                "repository": repo_href,
                "signed_collection": (
                    f"{gc.galaxy_root}pulp/api/v3/"
                    f"content/ansible/collection_versions/{collection_version_pk}/"
                ),
            },
            auth=("admin", "admin"),
        )
        assert "task" in response.json()

    time.sleep(SLEEP_SECONDS_ONETIME)  # wait for the task to finish

    # Assert that the collection is signed on v3 api
    collection = get_collection_from_repo(gc, "staging",
                                          artifact.namespace, artifact.name, artifact.version)
    assert len(collection["signatures"]) >= 1
    assert collection["signatures"][0]["signing_service"] is None


def test_move_with_no_signing_service_not_superuser_signature_required(
        flags, galaxy_client, settings, skip_if_not_require_signature_for_approval):
    """
    Test signature validation on the pulp {repo_href}/move_collection_version/ api when
    signatures are required.
    """
    # GALAXY_SIGNATURE_UPLOAD_ENABLED="false" in ephemeral env
    if not settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_CONTENT_APPROVAL is required to be enabled")

    # need the admin client
    gc_admin = galaxy_client("admin")

    # need a new regular user
    gc = galaxy_client("partner_engineer")

    # need a new namespace
    namespace = create_test_namespace(gc)

    # make the collection
    artifact = galaxy_build_collection(namespace=namespace)

    # use admin to upload the collection
    upload_task = upload_artifact(None, gc_admin, artifact)
    wait_for_task(gc_admin, upload_task)

    # create a signature
    signature = create_local_signature_for_tarball(artifact.filename)

    # upload the signature
    staging_href = get_repository_href(gc, "staging")
    collection_href = gc_admin.get(
        f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
    )["results"][0]["pulp_href"]

    signature_upload_response = requests.post(
        gc_admin.galaxy_root + "pulp/api/v3/content/ansible/collection_signatures/",
        verify=False,
        files={"file": signature},
        data={
            "repository": staging_href,
            "signed_collection": collection_href,
        },
        auth=(gc_admin.username, gc_admin.password),
    )
    wait_for_task(gc_admin, signature_upload_response.json())

    # use the PE user to approve the collection
    published_href = get_repository_href(gc, "published")
    move_content_between_repos(gc, [collection_href], staging_href,
                               [published_href])

    assert gc.get(f"v3/collections?name={artifact.name}")["meta"]["count"] == 1


def test_move_with_no_signing_service(flags, galaxy_client, settings, artifact,
                                      skip_if_not_require_signature_for_approval):
    """
    Test signature validation on the pulp {repo_href}/move_collection_version/ api when
    signatures are required.
    """
    if not settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_CONTENT_APPROVAL is required to be enabled")

    gc = galaxy_client("admin")
    upload_task = upload_artifact(None, gc, artifact)
    wait_for_task(gc, upload_task)
    staging_href = get_repository_href(gc, "staging")
    published_href = get_repository_href(gc, "published")

    collection_href = gc.get(
        f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
    )["results"][0]["pulp_href"]

    ####################################################
    # Test moving collection without signature
    ####################################################
    with pytest.raises(GalaxyClientError) as e:
        move_content_between_repos(gc, [collection_href], staging_href,
                                   [published_href])

    assert e.value.response.status_code == 400
    assert "Signatures are required" in e.value.response.text

    ####################################################
    # Test signing the collection before moving
    ####################################################

    # make signature
    signature = create_local_signature_for_tarball(artifact.filename)

    # upload signature

    staging_href = get_repository_href(gc, "staging")
    collection_href = gc.get(
        f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
    )["results"][0]["pulp_href"]

    signature_upload_response = requests.post(
        gc.galaxy_root + "pulp/api/v3/content/ansible/collection_signatures/",
        verify=False,
        files={"file": signature},
        data={
            "repository": staging_href,
            "signed_collection": collection_href,
        },
        auth=(gc.username, gc.password),
    )
    wait_for_task(gc, signature_upload_response.json())

    # move the collection
    move_content_between_repos(gc, [collection_href], staging_href,
                               [published_href])
    assert gc.get(f"v3/collections?name={artifact.name}")["meta"]["count"] == 1


def test_move_with_signing_service(flags, galaxy_client, settings, artifact,
                                   skip_if_not_require_signature_for_approval):
    """
    Test signature validation on the pulp {repo_href}/move_collection_version/ api when
    signatures are required.
    """

    if not settings.get("GALAXY_COLLECTION_SIGNING_SERVICE"):
        pytest.skip("GALAXY_COLLECTION_SIGNING_SERVICE is required to be set")

    gc = galaxy_client("admin")
    # this should never be None ...
    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE") or "ansible-default"
    upload_task = upload_artifact(None, gc, artifact)
    wait_for_task(gc, upload_task)

    staging_href = get_repository_href(gc, "staging")
    published_href = get_repository_href(gc, "published")
    collection_href = gc.get(
        f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
    )["results"][0]["pulp_href"]

    signing_href = gc.get(
        f"pulp/api/v3/signing-services/?name={signing_service}"
    )["results"][0]["pulp_href"]

    resp = gc.post(staging_href + "move_collection_version/", body={
        "collection_versions": [collection_href],
        "destination_repositories": [published_href],
        "signing_service": signing_href
    })

    wait_for_task(gc, resp)

    assert gc.get(f"v3/collections?name={artifact.name}")["meta"]["count"] == 1
