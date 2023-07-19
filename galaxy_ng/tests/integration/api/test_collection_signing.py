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
    copy_collection_version,
    create_unused_namespace,
    get_all_collections_by_repo,
    get_all_namespaces,
    get_client,
    set_certification,
    wait_for_task,
    create_local_signature_for_tarball,
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
def flags(api_client):
    api_prefix = api_client.config.get("api_prefix").rstrip("/")
    return api_client(f"{api_prefix}/_ui/v1/feature-flags/")


@pytest.fixture(scope="function", autouse=True)
def namespace(api_client):
    # ensure namespace exists
    existing = dict((x["name"], x) for x in get_all_namespaces(api_client=api_client))
    if NAMESPACE not in existing:
        payload = {"name": NAMESPACE, "groups": []}
        api_prefix = api_client.config.get("api_prefix").rstrip("/")
        api_client(f"{api_prefix}/v3/namespaces/", args=payload, method="POST")
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
    api_prefix = api_client.config.get("api_prefix").rstrip("/")
    sign_url = sign_url or f"{api_prefix}/_ui/v1/collection_signing/"
    sign_payload = {"signing_service": signing_service, **payload}

    '''
    # need to get the x-repo list now ...
    cvs = get_all_repository_collection_versions(api_client=api_client)
    import epdb; epdb.st()
    '''

    resp = api_client(sign_url, method="POST", args=sign_payload)
    log.info("Sign Task: %s", resp)
    # FIXME - pulp tasks do not seem to accept token auth, so no way to check task progress
    time.sleep(SLEEP_SECONDS_ONETIME)
    return resp


@pytest.mark.collection_signing
@pytest.mark.collection_move
@pytest.mark.deployment_standalone
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
    api_prefix = api_client.config.get("api_prefix").rstrip("/")
    collection = api_client(
        f"{api_prefix}/content/published/v3/collections/"
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
        f"{api_prefix}/_ui/v1/repo/published/"
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
@pytest.mark.deployment_standalone
@pytest.mark.parametrize(
    "sign_url",
    [
        "{api_prefix}/_ui/v1/collection_signing/",
        "{api_prefix}/_ui/v1/collection_signing/{distro_base_path}/",
        "{api_prefix}/_ui/v1/collection_signing/{distro_base_path}/{namespace}/",
        (
            "{api_prefix}/_ui/v1/collection_signing/"
            "{distro_base_path}/{namespace}/{collection}/"
        ),
        (
            "{api_prefix}/_ui/v1/collection_signing/"
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
    api_prefix = api_client.config.get("api_prefix").rstrip("/")
    sign_payload = {
        "api_prefix": api_prefix,
        "distro_base_path": "staging",
        "namespace": NAMESPACE,
        "collection": artifact.name,
        "version": artifact.version,
    }
    sign_on_demand(api_client, signing_service, sign_url.format(**sign_payload), **sign_payload)
    # Assert that the collection is signed on v3 api
    collection = api_client(
        f"{api_prefix}/content/staging/v3/collections/"
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
        f"{api_prefix}/_ui/v1/repo/staging/"
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
        f"{api_prefix}/_ui/v1/repo/staging/{NAMESPACE}/{artifact.name}"
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
@pytest.mark.deployment_standalone
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
        api_prefix = api_client.config.get("api_prefix").rstrip("/")
        collection = api_client(
            f"{api_prefix}/content/staging/v3/collections/"
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
    api_prefix = api_client.config.get("api_prefix").rstrip("/")
    collection = api_client(
        f"{api_prefix}/content/published/v3/collections/"
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
        f"{api_prefix}/_ui/v1/repo/published/"
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
def test_copy_collection_without_signatures(api_client, config, settings, flags, upload_artifact):
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
    import_and_wait(api_client, artifact, upload_artifact, config)

    # Collection must be on /staging/
    collections = get_all_collections_by_repo(api_client)
    assert ckey in collections["staging"]

    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")

    # Sign the collection while still on staging
    sign_payload = {
        "distro_base_path": "staging",
        "namespace": NAMESPACE,
        "collection": artifact.name,
        "version": artifact.version,
    }
    sign_on_demand(api_client, signing_service, **sign_payload)

    # Assert that the collection is signed on v3 api
    api_prefix = api_client.config.get("api_prefix").rstrip("/")
    collection = api_client(
        f"{api_prefix}/content/staging/v3/collections/"
        f"{artifact.namespace}/{artifact.name}/versions/{artifact.version}/"
    )

    assert len(collection["signatures"]) >= 1
    assert collection["signatures"][0]["signing_service"] == signing_service

    # Copy the collection to /community/
    copy_result = copy_collection_version(
        api_client,
        artifact,
        src_repo_name="staging",
        dest_repo_name="community"
    )

    assert copy_result["namespace"]["name"] == artifact.namespace
    assert copy_result["name"] == artifact.name
    assert copy_result["version"] == artifact.version
    assert copy_result["href"] is not None
    expected_tags = ["tools", "copytest"]
    actual_tags = copy_result["metadata"]["tags"]
    assert sorted(actual_tags) == sorted(expected_tags)
    assert len(copy_result["signatures"]) == 1

    # Assert that the collection is signed on ui/stating but not on ui/community
    collections = get_all_collections_by_repo(api_client)
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
def test_upload_signature(config, require_auth, settings, upload_artifact):
    """
    1. If staging repository doesn't have a gpgkey, skip test
    2. Generate a collection
    3. Upload collection to staging
    4. Sign the collection MANIFEST.json file
    5. Upload the signature to staging
    6. assert collection signature task has spawned
    """
    api_client = get_client(config=config, request_token=True, require_auth=require_auth)

    if not settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_CONTENT_APPROVAL is not set")

    api_prefix = api_client.config.get("api_prefix").rstrip("/")
    distributions = api_client(f"{api_prefix}/_ui/v1/distributions/")
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
                    f"{api_prefix}/pulp/api/v3/"
                    f"content/ansible/collection_versions/{collection_version_pk}/"
                ),
            },
            auth=("admin", "admin"),
        )
        assert "task" in response.json()

    time.sleep(SLEEP_SECONDS_ONETIME)  # wait for the task to finish

    # Assert that the collection is signed on v3 api
    collection = api_client(
        f"{api_prefix}/content/staging/v3/collections/"
        f"{artifact.namespace}/{artifact.name}/versions/{artifact.version}/"
    )
    assert len(collection["signatures"]) >= 1
    assert collection["signatures"][0]["signing_service"] is None


def test_move_with_no_signing_service_not_superuser_signature_required(
    ansible_config,
    upload_artifact,
    settings
):
    """
    Test signature validation on the pulp {repo_href}/move_collection_version/ api when
    signatures are required.
    """
    if not settings.get("GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL is required to be enabled")

    if not settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_CONTENT_APPROVAL is required to be enabled")

    # need the admin client
    admin_config = ansible_config("admin")
    admin_client = get_client(admin_config, request_token=True, require_auth=True)

    # need a new regular user
    partner_eng_config = ansible_config("partner_engineer")
    partner_eng_client = get_client(partner_eng_config, request_token=True, require_auth=True)

    # need a new namespace
    namespace = create_unused_namespace(api_client=admin_client)

    # make the collection
    artifact = galaxy_build_collection(namespace=namespace)

    # use admin to upload the collection
    upload_task = upload_artifact(admin_config, admin_client, artifact)
    resp = wait_for_task(admin_client, upload_task)

    # create a signature
    signature = create_local_signature_for_tarball(artifact.filename)

    # upload the signature
    baseurl = admin_config.get('url').rstrip('/') + '/' + 'pulp/api/v3/'
    staging_href = admin_client(
        "pulp/api/v3/repositories/ansible/ansible/?name=staging")["results"][0]["pulp_href"]
    collection_href = admin_client(
        f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
    )["results"][0]["pulp_href"]
    signature_upload_response = requests.post(
        baseurl + "content/ansible/collection_signatures/",
        files={"file": signature},
        data={
            "repository": staging_href,
            "signed_collection": collection_href,
        },
        auth=(admin_config.get('username'), admin_config.get('password')),
    )
    wait_for_task(admin_client, signature_upload_response.json())

    # use the PE user to approve the collection
    published_href = partner_eng_client(
        "pulp/api/v3/repositories/ansible/ansible/?name=published")["results"][0]["pulp_href"]
    resp = requests.post(
        partner_eng_config["server"] + staging_href + "move_collection_version/",
        json={
            "collection_versions": [collection_href],
            "destination_repositories": [published_href]
        },
        auth=(partner_eng_config["username"], partner_eng_config["password"])
    )

    assert resp.status_code == 202
    assert "task" in resp.json()
    wait_for_task(partner_eng_client, resp.json())
    assert partner_eng_client(f"v3/collections?name={artifact.name}")["meta"]["count"] == 1


def test_move_with_no_signing_service(ansible_config, artifact, upload_artifact, settings):
    """
    Test signature validation on the pulp {repo_href}/move_collection_version/ api when
    signatures are required.
    """
    if not settings.get("GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL is required to be enabled")

    if not settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_CONTENT_APPROVAL is required to be enabled")

    config = ansible_config("admin")
    api_client = get_client(config, request_token=True, require_auth=True)

    resp = upload_artifact(config, api_client, artifact)
    resp = wait_for_task(api_client, resp)
    staging_href = api_client(
        "pulp/api/v3/repositories/ansible/ansible/?name=staging")["results"][0]["pulp_href"]
    published_href = api_client(
        "pulp/api/v3/repositories/ansible/ansible/?name=published")["results"][0]["pulp_href"]
    collection_href = api_client(
        f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
    )["results"][0]["pulp_href"]

    ####################################################
    # Test moving collection without signature
    ####################################################

    resp = requests.post(
        config["server"] + staging_href + "move_collection_version/",
        json={
            "collection_versions": [collection_href],
            "destination_repositories": [published_href]
        },
        auth=(config["username"], config["password"])
    )

    assert resp.status_code == 400
    err = resp.json().get("collection_versions", None)
    assert err is not None
    assert "Signatures are required" in err

    ####################################################
    # Test signing the collection before moving
    ####################################################

    # make signature
    signature = create_local_signature_for_tarball(artifact.filename)

    # upload signature
    baseurl = config.get('url').rstrip('/') + '/' + 'pulp/api/v3/'
    signature_upload_response = requests.post(
        baseurl + "content/ansible/collection_signatures/",
        files={"file": signature},
        data={
            "repository": staging_href,
            "signed_collection": collection_href,
        },
        auth=(config.get('username'), config.get('password')),
    )
    wait_for_task(api_client, signature_upload_response.json())

    # move the collection
    resp = requests.post(
        config["server"] + staging_href + "move_collection_version/",
        json={
            "collection_versions": [collection_href],
            "destination_repositories": [published_href]
        },
        auth=(config["username"], config["password"])
    )

    assert resp.status_code == 202
    assert "task" in resp.json()

    wait_for_task(api_client, resp.json())

    assert api_client(f"v3/collections?name={artifact.name}")["meta"]["count"] == 1


def test_move_with_signing_service(ansible_config, artifact, upload_artifact, settings):
    """
    Test signature validation on the pulp {repo_href}/move_collection_version/ api when
    signatures are required.
    """

    if not settings.get("GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL is required to be enabled")

    if not settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_CONTENT_APPROVAL is required to be enabled")

    if not settings.get("GALAXY_COLLECTION_SIGNING_SERVICE"):
        pytest.skip("GALAXY_COLLECTION_SIGNING_SERVICE is required to be set")

    config = ansible_config("admin")
    api_client = get_client(config, request_token=True, require_auth=True)

    # this should never be None ...
    signing_service = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE") or "ansible-default"

    resp = upload_artifact(config, api_client, artifact)
    resp = wait_for_task(api_client, resp)
    staging_href = api_client(
        "pulp/api/v3/repositories/ansible/ansible/?name=staging")["results"][0]["pulp_href"]
    published_href = api_client(
        "pulp/api/v3/repositories/ansible/ansible/?name=published")["results"][0]["pulp_href"]
    collection_href = api_client(
        f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
    )["results"][0]["pulp_href"]
    signing_href = api_client(
        f"pulp/api/v3/signing-services/?name={signing_service}"
    )["results"][0]["pulp_href"]

    resp = requests.post(
        config["server"] + staging_href + "move_collection_version/",
        json={
            "collection_versions": [collection_href],
            "destination_repositories": [published_href],
            "signing_service": signing_href
        },
        auth=(config["username"], config["password"])
    )

    assert resp.status_code == 202
    assert "task" in resp.json()

    wait_for_task(api_client, resp.json())

    assert api_client(f"v3/collections?name={artifact.name}")["meta"]["count"] == 1
