"""Tests for verifying PQC (Post-Quantum Cryptography) signature support.

When syncing container images from registry.access.redhat.com, images like
ubi10-micro:latest carry both traditional GPG signatures and PQC (ML-DSA-87)
signatures. This test ensures galaxy_ng (via pulp_container) can handle both.

Epic: https://redhat.atlassian.net/browse/AAP-71604
Feature: https://github.com/pulp/pulp_container/pull/2291
"""
import contextlib
import logging
import os
import shutil
import uuid
import pytest

from galaxy_ng.tests.integration.utils.iqe_utils import run_container_command
from galaxykit.utils import wait_for_task

logger = logging.getLogger(__name__)


# Red Hat container registry and sigstore URLs
REDHAT_REGISTRY_V2 = "https://registry.access.redhat.com"
REDHAT_SIGSTORE_URL = (
    "https://access.redhat.com/webassets/docker/content/sigstore"
)

# ubi10-micro carries both traditional and PQC signatures
UBI10_MICRO_UPSTREAM_NAME = "ubi10-micro"
UBI10_MICRO_TAG = "latest"

# Product signing keys are published on https://access.redhat.com/security/team/key
# Traditional Red Hat release signing key IDs
REDHAT_RELEASE_KEY_IDS = ["199E2F91FD431D51", "E60D446E63405576"]

# Red Hat PQC (ML-DSA-87) signing key ID
REDHAT_PQC_KEY_ID = "FCD355B305707A62"


@pytest.mark.deployment_standalone
def test_sync_image_with_pqc_signatures(galaxy_client):
    """Sync ubi10-micro:latest and verify traditional and PQC signatures are parsed.

    Syncs the image from registry.access.redhat.com via sigstore, then checks
    that both traditional GPG and PQC (ML-DSA-87) signatures are present
    for every manifest in the manifest list.
    """
    gc = galaxy_client("admin")
    suffix = uuid.uuid4().hex[:8]

    # Create a container remote pointing to the Red Hat registry
    remote = gc.post(
        "pulp/api/v3/remotes/container/container/",
        body={
            "name": f"test-pqc-remote-{suffix}",
            "url": REDHAT_REGISTRY_V2,
            "upstream_name": UBI10_MICRO_UPSTREAM_NAME,
            "policy": "on_demand",
            "include_tags": [UBI10_MICRO_TAG],
            "sigstore": REDHAT_SIGSTORE_URL,
        },
    )
    remote_href = remote["pulp_href"]

    # Create a container repository to sync into
    repo = gc.post(
        "pulp/api/v3/repositories/container/container/",
        body={"name": f"test-pqc-repo-{suffix}"},
    )
    repo_href = repo["pulp_href"]

    try:
        # Sync the repository from the remote
        sync_response = gc.post(
            f"{repo_href}sync/",
            body={"remote": remote_href, "signed_only": False},
        )
        task_result = wait_for_task(gc, sync_response)
        assert task_result["state"] == "completed"

        # Re-read the repo to get the latest version href
        repo = gc.get(repo_href)
        latest_version = repo["latest_version_href"]

        # Verify the expected tag was synced
        tags_response = gc.get(
            f"pulp/api/v3/content/container/tags/"
            f"?repository_version={latest_version}"
        )
        assert tags_response["count"] == 1
        assert tags_response["results"][0]["name"] == UBI10_MICRO_TAG

        # Collect all signatures (handling pagination)
        sig_response = gc.get(
            f"pulp/api/v3/content/container/signatures/"
            f"?repository_version={latest_version}"
        )
        assert sig_response["count"] > 0
        all_signatures = list(sig_response["results"])
        while sig_response.get("next"):
            sig_response = gc.get(sig_response["next"])
            all_signatures.extend(sig_response["results"])

        # Assert that at least one traditional Red Hat signing key is present
        found_key_ids = {s["key_id"] for s in all_signatures}
        assert any(kid in REDHAT_RELEASE_KEY_IDS for kid in found_key_ids), (
            f"No signature found with traditional Red Hat key_ids "
            f"{REDHAT_RELEASE_KEY_IDS}; found key_ids: {sorted(found_key_ids)}"
        )

        # Assert PQC (ML-DSA-87) signature is present
        assert REDHAT_PQC_KEY_ID in found_key_ids, (
            f"No PQC signature found with key_id {REDHAT_PQC_KEY_ID!r}; "
            f"found key_ids: {sorted(found_key_ids)}"
        )

        # ubi10-micro:latest is a manifest list; verify every listed manifest
        # has at least one signature
        tag_manifest_href = tags_response["results"][0]["tagged_manifest"]
        manifest_list = gc.get(tag_manifest_href)
        for lm_href in manifest_list.get("listed_manifests", []):
            lm = gc.get(lm_href)
            lm_sigs = [
                s for s in all_signatures
                if s["signed_manifest"] == lm["pulp_href"]
            ]
            assert len(lm_sigs) > 0, (
                f"No signatures found for manifest {lm['digest']}"
            )
            assert all(s["name"].startswith(lm["digest"]) for s in lm_sigs)

    finally:
        # Cleanup: remove the test repository and remote
        for href in (repo_href, remote_href):
            try:
                gc.delete(href, parse_json=False)
            except Exception:
                logger.warning("Cleanup failed for %s", href, exc_info=True)


@pytest.mark.deployment_standalone
def test_push_image_with_pqc_signatures_via_skopeo(ansible_config, galaxy_client):
    """Push ubi10-micro:latest via skopeo and verify traditional and PQC signatures are parsed.

    Uses skopeo copy to transfer the image directly from registry.access.redhat.com
    to the local registry, preserving signatures. Then checks that both traditional
    GPG and PQC (ML-DSA-87) signatures are present in the push repository.
    """
    if not shutil.which("skopeo"):
        pytest.skip("skopeo is not installed")

    config = ansible_config("admin")
    container_registry = config["container_registry"]
    suffix = uuid.uuid4().hex[:8]
    repo_name = f"test-pqc-push-{suffix}"
    registry_name = REDHAT_REGISTRY_V2.replace('https://', '')

    src = f"docker://{registry_name}/{UBI10_MICRO_UPSTREAM_NAME}:{UBI10_MICRO_TAG}"
    dest = f"docker://{container_registry}/{repo_name}:{UBI10_MICRO_TAG}"

    # Configure registries.d so skopeo knows where to find signatures for
    # registry.access.redhat.com. Red Hat stores container image signatures
    # in an external sigstore, not in the registry's Extensions API.
    # Without this config, skopeo copies only manifests and blobs — no signatures.
    registries_d = os.path.expanduser("~/.config/containers/registries.d")
    os.makedirs(registries_d, exist_ok=True)
    sigstore_config_path = os.path.join(registries_d, "test-redhat-sigstore.yaml")
    with open(sigstore_config_path, "w") as f:
        f.write(
            "docker:\n"
            "  registry.access.redhat.com:\n"
            f"    lookaside: {REDHAT_SIGSTORE_URL}\n"
        )

    gc = galaxy_client("admin")
    repo_href = None

    try:
        # Copy the image directly from Red Hat registry to the local registry.
        # With registries.d configured, skopeo reads signatures from the sigstore
        # and pushes them to the destination via the Docker v2 Extensions API.
        run_container_command(
            [
                "skopeo", "copy",
                "--dest-tls-verify=false",
                "--dest-creds", f"{config['username']}:{config['password']}",
                src, dest,
            ],
            "Skopeo copy",
            timeout=300,
        )
        # Verify the push-repository was created
        repos = gc.get(
            f"pulp/api/v3/repositories/container/container-push/"
            f"?name={repo_name}"
        )
        assert repos["count"] == 1, (
            f"Expected 1 push-repository named '{repo_name}', "
            f"got {repos['count']}"
        )
        repo_href = repos["results"][0]["pulp_href"]
        latest_version = repos["results"][0]["latest_version_href"]

        # Verify the tag is present
        tags_response = gc.get(
            f"pulp/api/v3/content/container/tags/"
            f"?repository_version={latest_version}"
        )
        tag_names = [t["name"] for t in tags_response["results"]]
        assert UBI10_MICRO_TAG in tag_names, (
            f"Expected tag '{UBI10_MICRO_TAG}' in repository; "
            f"found tags: {tag_names}"
        )

        # Verify manifests were pushed (ubi10-micro is a manifest list)
        manifests = gc.get(
            f"pulp/api/v3/content/container/manifests/"
            f"?repository_version={latest_version}"
        )
        assert manifests["count"] > 0, "No manifests found after push"

        # Collect all signatures (handling pagination)
        sig_response = gc.get(
            f"pulp/api/v3/content/container/signatures/"
            f"?repository_version={latest_version}"
        )
        assert sig_response["count"] > 0, "No signatures found after push"
        all_signatures = list(sig_response["results"])
        while sig_response.get("next"):
            sig_response = gc.get(sig_response["next"])
            all_signatures.extend(sig_response["results"])

        # Assert that at least one traditional Red Hat signing key is present
        found_key_ids = {s["key_id"] for s in all_signatures}
        assert any(kid in REDHAT_RELEASE_KEY_IDS for kid in found_key_ids), (
            f"No signature found with traditional Red Hat key_ids "
            f"{REDHAT_RELEASE_KEY_IDS}; found key_ids: {sorted(found_key_ids)}"
        )

        # Assert PQC (ML-DSA-87) signature is present
        assert REDHAT_PQC_KEY_ID in found_key_ids, (
            f"No PQC signature found with key_id {REDHAT_PQC_KEY_ID!r}; "
            f"found key_ids: {sorted(found_key_ids)}"
        )

    finally:
        # Clean up the temporary registries.d config file
        with contextlib.suppress(OSError):
            os.unlink(sigstore_config_path)
        if repo_href:
            try:
                gc.delete(repo_href, parse_json=False)
            except Exception:
                logger.warning("Cleanup failed for %s", repo_href, exc_info=True)
