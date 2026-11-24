"""Tests for verifying SHA-1 self-signature key support in collection signing.

GnuPG v2.0.x keys used SHA-1 for key self-signatures (UID binding certifications).
Modern pysequoia's default policy rejects these keys, preventing signature
verification for collections signed with such keys (e.g. the Ansible Automation
Hub signing key).

The galaxy_ng container patches pysequoia to use a system crypto-policy that
allows SHA-1 for signature verification, enabling these legacy keys to work.

Related:
- d63033c1: hotfix pysequoia and crypto-policies for sha-1 support
- a9f2d8e7: allow PQC algos in sequoia config
"""

import logging
import os
import subprocess
import tarfile
import tempfile
import uuid

import pytest
import requests

from orionutils.generator import build_collection

from galaxykit.collections import upload_artifact
from galaxykit.utils import wait_for_task

logger = logging.getLogger(__name__)

NAMESPACE = "signing"


@pytest.fixture
def sha1_gpg_key(tmp_path):
    """Generate an ephemeral GPG keypair whose self-signature uses SHA-1.

    This simulates legacy keys created with GnuPG v2.0.x, which defaulted
    to SHA-1 for certification self-signatures.
    """
    gnupg_home = tmp_path / "gnupg"
    gnupg_home.mkdir(mode=0o700)

    gpg_conf = gnupg_home / "gpg.conf"
    gpg_conf.write_text("cert-digest-algo SHA1\n")

    email = f"sha1-test-{uuid.uuid4().hex[:8]}@example.com"

    result = subprocess.run(
        [
            "gpg", "--batch", "--homedir", str(gnupg_home),
            "--passphrase", "", "--quick-gen-key",
            f"SHA1 Test <{email}>", "rsa2048", "sign", "never",
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"Failed to generate SHA-1 self-sig key: {result.stderr}")

    pubkey_result = subprocess.run(
        ["gpg", "--homedir", str(gnupg_home), "--armor", "--export", email],
        capture_output=True, text=True,
    )
    public_key = pubkey_result.stdout

    fp_result = subprocess.run(
        [
            "gpg", "--homedir", str(gnupg_home), "--with-colons",
            "--list-keys", email,
        ],
        capture_output=True, text=True,
    )
    fingerprint = None
    for line in fp_result.stdout.splitlines():
        if line.startswith("fpr:"):
            fingerprint = line.split(":")[9]
            break

    if not fingerprint:
        pytest.skip("Could not extract fingerprint from generated key")

    return {
        "gnupg_home": str(gnupg_home),
        "email": email,
        "public_key": public_key,
        "fingerprint": fingerprint,
    }


@pytest.fixture(autouse=True)
def namespace(galaxy_client):
    gc = galaxy_client("admin")
    existing = gc.get("v3/namespaces/?limit=100")
    names = {ns["name"] for ns in existing.get("data", existing.get("results", []))}
    if NAMESPACE not in names:
        gc.post("v3/namespaces/", body={"name": NAMESPACE, "groups": []})


@pytest.mark.deployment_standalone
@pytest.mark.collection_signing
@pytest.mark.skip_in_gw
def test_signature_upload_with_sha1_self_sig_key(galaxy_client, sha1_gpg_key):
    """Verify that signature upload succeeds when the repository gpgkey has SHA-1 self-sigs.

    This exercises the pysequoia SHA-1 crypto-policy fix end-to-end.  Without the
    fix, ``gpg_verify()`` fails at ``Cert.split_bytes()`` because pysequoia's
    default policy rejects the SHA-1 certification self-signature on the key.

    Flow:
        1. Create a repository whose ``gpgkey`` is a cert with SHA-1 self-sigs.
        2. Upload a collection and add it to the repository.
        3. Sign the MANIFEST.json locally with the SHA-1 key.
        4. Upload the detached signature — the server calls ``gpg_verify``
           with the repository's gpgkey, which forces pysequoia to parse the
           SHA-1 self-sig cert.
        5. Assert that the verification task completes successfully.
    """
    gc = galaxy_client("admin")
    suffix = uuid.uuid4().hex[:8]

    repo = gc.post(
        "pulp/api/v3/repositories/ansible/ansible/",
        body={
            "name": f"test-sha1-{suffix}",
            "gpgkey": sha1_gpg_key["public_key"],
        },
    )
    repo_href = repo["pulp_href"]

    try:
        artifact = build_collection(
            "skeleton",
            config={"namespace": NAMESPACE, "tags": ["sha1test"]},
        )

        resp = upload_artifact(None, gc, artifact)
        resp = wait_for_task(gc, resp)
        assert resp["state"] == "completed"

        cv_response = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/"
            f"?namespace={NAMESPACE}&name={artifact.name}"
            f"&version={artifact.version}"
        )
        assert cv_response["count"] >= 1
        cv_href = cv_response["results"][0]["pulp_href"]

        modify_resp = gc.post(
            f"{repo_href}modify/",
            body={"add_content_units": [cv_href]},
        )
        wait_for_task(gc, modify_resp)

        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(artifact.filename, "r:gz") as tar:
                tar.extractall(tmpdir)

            manifest_path = os.path.join(tmpdir, "MANIFEST.json")
            sig_path = f"{manifest_path}.asc"

            sign_result = subprocess.run(
                [
                    "gpg", "--batch",
                    "--homedir", sha1_gpg_key["gnupg_home"],
                    "--pinentry-mode", "loopback",
                    "--passphrase", "",
                    "--yes",
                    "--default-key", sha1_gpg_key["email"],
                    "--detach-sign", "--armor",
                    "--output", sig_path,
                    manifest_path,
                ],
                capture_output=True, text=True,
            )
            assert sign_result.returncode == 0, (
                f"GPG signing failed: {sign_result.stderr}"
            )

            with open(sig_path, "rb") as sig_file:
                upload_response = requests.post(
                    gc.galaxy_root
                    + "pulp/api/v3/content/ansible/collection_signatures/",
                    verify=False,
                    files={"file": sig_file},
                    data={
                        "repository": repo_href,
                        "signed_collection": cv_href,
                    },
                    auth=(gc.username, gc.password),
                )

            assert upload_response.status_code in (200, 201, 202), (
                f"Signature upload failed: {upload_response.status_code} "
                f"{upload_response.text}"
            )
            assert "task" in upload_response.json(), (
                f"No task in response: {upload_response.json()}"
            )

            task_result = wait_for_task(gc, upload_response.json())
            assert task_result["state"] == "completed", (
                f"Signature verification task failed (pysequoia likely rejected "
                f"the SHA-1 self-sig cert): {task_result}"
            )

        repo_refreshed = gc.get(repo_href)
        latest_version = repo_refreshed["latest_version_href"]

        sigs = gc.get(
            f"pulp/api/v3/content/ansible/collection_signatures/"
            f"?repository_version={latest_version}"
        )
        assert sigs["count"] >= 1, "Signature not found in repository"

        sig = sigs["results"][0]
        assert sig["pubkey_fingerprint"].upper() == sha1_gpg_key["fingerprint"].upper()

    finally:
        try:
            gc.delete(repo_href, parse_json=False)
        except Exception:
            logger.warning("Cleanup failed for %s", repo_href, exc_info=True)


@pytest.mark.deployment_standalone
@pytest.mark.collection_signing
@pytest.mark.skip_in_gw
def test_sha1_key_rejected_without_crypto_policy(galaxy_client, sha1_gpg_key):
    """Negative-path documentation: show what gpg_verify returns for SHA-1 keys.

    This test verifies that the server accepts the SHA-1 self-sig key.  If the
    crypto-policy fix were reverted, the ``verify_signature_upload`` task would
    fail with an error like:

        "Policy rejected non-revocation signature … SHA1 is not considered
        secure since 2023-02-01T00:00:00Z"

    By asserting the happy path here we create a regression guard: if this test
    starts failing with that error message, it means the SHA-1 crypto-policy or
    pysequoia patch was reverted or misconfigured.
    """
    gc = galaxy_client("admin")
    suffix = uuid.uuid4().hex[:8]

    repo = gc.post(
        "pulp/api/v3/repositories/ansible/ansible/",
        body={
            "name": f"test-sha1-regression-{suffix}",
            "gpgkey": sha1_gpg_key["public_key"],
        },
    )
    repo_href = repo["pulp_href"]

    try:
        artifact = build_collection(
            "skeleton",
            config={"namespace": NAMESPACE, "tags": ["sha1regression"]},
        )
        resp = upload_artifact(None, gc, artifact)
        resp = wait_for_task(gc, resp)
        assert resp["state"] == "completed"

        cv_response = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/"
            f"?namespace={NAMESPACE}&name={artifact.name}"
            f"&version={artifact.version}"
        )
        cv_href = cv_response["results"][0]["pulp_href"]

        modify_resp = gc.post(
            f"{repo_href}modify/",
            body={"add_content_units": [cv_href]},
        )
        wait_for_task(gc, modify_resp)

        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(artifact.filename, "r:gz") as tar:
                tar.extractall(tmpdir)

            manifest_path = os.path.join(tmpdir, "MANIFEST.json")
            sig_path = f"{manifest_path}.asc"

            subprocess.run(
                [
                    "gpg", "--batch",
                    "--homedir", sha1_gpg_key["gnupg_home"],
                    "--pinentry-mode", "loopback",
                    "--passphrase", "",
                    "--yes",
                    "--default-key", sha1_gpg_key["email"],
                    "--detach-sign", "--armor",
                    "--output", sig_path,
                    manifest_path,
                ],
                capture_output=True, text=True, check=True,
            )

            with open(sig_path, "rb") as sig_file:
                upload_response = requests.post(
                    gc.galaxy_root
                    + "pulp/api/v3/content/ansible/collection_signatures/",
                    verify=False,
                    files={"file": sig_file},
                    data={
                        "repository": repo_href,
                        "signed_collection": cv_href,
                    },
                    auth=(gc.username, gc.password),
                )

            task_result = wait_for_task(gc, upload_response.json())

            assert task_result["state"] == "completed", (
                "Signature verification failed — this likely means the SHA-1 "
                "crypto-policy fix was reverted or pysequoia was updated "
                f"without preserving SHA-1 support. Task error: {task_result}"
            )

    finally:
        try:
            gc.delete(repo_href, parse_json=False)
        except Exception:
            logger.warning("Cleanup failed for %s", repo_href, exc_info=True)
