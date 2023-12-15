import logging
import subprocess
import tempfile

import pytest
from orionutils.generator import build_collection, randstr

from galaxykit.collections import upload_artifact
from galaxykit.utils import wait_for_task
from galaxykit.collections import upload_artifact
from galaxykit.utils import GalaxyClientError, wait_for_task
from ..conftest import is_hub_4_5
from ..constants import USERNAME_PUBLISHER
from ..utils import (
    CollectionInspector,
    get_client,
    set_certification,
)

logger = logging.getLogger(__name__)


# TODO Refactor get_client to provide access to bearer token
@pytest.mark.deployment_standalone
@pytest.mark.installer_smoke_test
def test_download_artifact(ansible_config, galaxy_client):
    gc = galaxy_client("partner_engineer")

    # create, upload and certify a collection
    namespace = USERNAME_PUBLISHER
    name = f"{USERNAME_PUBLISHER}_{randstr(8)}"
    version = "1.0.0"
    artifact = build_collection("skeleton", config={
        "namespace": namespace,
        "name": name,
        "version": version,
    })
    resp = upload_artifact(None, gc, artifact)
    logger.debug("Waiting for upload to be completed")
    resp = wait_for_task(gc, resp)
    assert resp["state"] == "completed"
    hub_4_5 = is_hub_4_5(ansible_config)
    set_certification(ansible_config(), gc, artifact, hub_4_5=hub_4_5)

    with tempfile.TemporaryDirectory() as dir:
        filename = f"{namespace}-{name}-{version}.tar.gz"
        tarball_path = f"{dir}/{filename}"
        url = f"{gc.galaxy_root}v3/plugin/ansible/content/published/collections/artifacts/{filename}"

        cmd = [
            "curl",
            "--retry",
            "5",
            "-L",
            "-H",
            "'Content-Type: application/json'",
            "-u",
            f"{gc.username}:{gc.password}",
            "-o",
            tarball_path,
            url,
            "--insecure"
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        returncode = proc.wait()
        assert returncode == 0

        # Extract tarball, verify information in manifest
        ci = CollectionInspector(tarball=tarball_path)
        assert ci.namespace == namespace
        assert ci.name == name
        assert ci.version == version


# TODO: make download logic more DRY in these tests
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.all
def test_download_artifact_validated(ansible_config, galaxy_client):
    gc = galaxy_client("partner_engineer")

    # create, upload and certify a collection
    namespace = USERNAME_PUBLISHER
    name = f"{USERNAME_PUBLISHER}_{randstr(8)}"
    version = "1.0.0"
    artifact = build_collection("skeleton", config={
        "namespace": namespace,
        "name": name,
        "version": version,
    })
    resp = upload_artifact(None, gc, artifact)
    logger.debug("Waiting for upload to be completed")
    resp = wait_for_task(gc, resp)
    assert resp["state"] == "completed"
    set_certification(ansible_config(), gc, artifact, level="validated")

    with tempfile.TemporaryDirectory() as dir:
        filename = f"{artifact.namespace}-{artifact.name}-{artifact.version}.tar.gz"
        tarball_path = f"{dir}/{filename}"
        url = f"{gc.galaxy_root}v3/plugin/ansible/content/validated/collections/artifacts/{filename}"

        cmd = [
            "curl",
            "--retry",
            "5",
            "-L",
            "-H",
            "'Content-Type: application/json'",
            "-u",
            f"{gc.username}:{gc.password}",
            "-o",
            tarball_path,
            url,
            "--insecure"
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        returncode = proc.wait()
        assert returncode == 0

        # Extract tarball, verify information in manifest
        ci = CollectionInspector(tarball=tarball_path)
        assert ci.namespace == artifact.namespace
        assert ci.name == artifact.name
        assert ci.version == artifact.version
