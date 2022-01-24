"""test_cli_flow.py - Tests against the basic CLI publish/install behaviors."""
import json
import logging
import os
import sys
from subprocess import run
from unittest.mock import patch

import pytest
from orionutils.generator import build_collection
from orionutils.utils import increment_version

from ..constants import USERNAME_PUBLISHER
from ..utils import ansible_galaxy
from ..utils import CapturingGalaxyError
from ..utils import get_client
from ..utils import get_collection_full_path
from ..utils import set_certification


pytestmark = pytest.mark.qa  # noqa: F821
logger = logging.getLogger(__name__)


@pytest.mark.cli
def test_publish_newer_version_collection(ansible_config):
    """Test whether a newer version of collection can be installed after being published.

    If the collection version was not certified the version to be installed
    has to be specified during installation.
    """

    print('')
    client = get_client(ansible_config("ansible_insights"))

    # Publish first collection version
    ansible_config("ansible_partner", namespace=USERNAME_PUBLISHER)
    collection = build_collection("skeleton", config={"namespace": USERNAME_PUBLISHER})
    publish_pid_1 = ansible_galaxy(
        f"collection publish {collection.filename}",
        ansible_config=ansible_config("ansible_insights")
    )
    print(f'PUBLISH 1 RC: {publish_pid_1.returncode}')
    assert publish_pid_1.returncode == 0

    cert1 = set_certification(client, collection)
    print(f'SET CERTIFICATION 2: {cert1}')

    # Increase collection version
    new_version = increment_version(collection.version)
    collection = build_collection(
        "skeleton",
        key=collection.key,
        config={"namespace": USERNAME_PUBLISHER, "version": new_version},
    )

    # Publish newer collection version
    publish_pid_2 = ansible_galaxy(
        f"collection publish {collection.filename}",
        ansible_config=ansible_config("ansible_partner", namespace=USERNAME_PUBLISHER)
    )
    print(f'PUBLISH 2 RC: {publish_pid_2.returncode}')
    assert publish_pid_2.returncode == 0

    cert2 = set_certification(client, collection)
    print(f'SET CERTIFICATION 2: {cert2}')

    # Install newer collection version
    ansible_config("ansible_partner")
    install_pid = ansible_galaxy(
        f"collection install {collection.namespace}.{collection.name}:{collection.version}",
        ansible_config=ansible_config("ansible_partner"),
        cleanup=False,
        check_retcode=False
    )
    print(install_pid.stdout.decode('utf-8'))
    assert install_pid.returncode == 0

    # Verify installed collection
    collection_path = get_collection_full_path(USERNAME_PUBLISHER, collection.name)
    with open(os.path.join(collection_path, "MANIFEST.json")) as manifest_json:
        data = json.load(manifest_json)

    #import epdb; epdb.st()

    assert data["collection_info"]["version"] == collection.version


@pytest.mark.cli
@pytest.mark.skip(reason="fails in ephemeral")
def test_publish_newer_certified_collection_version(ansible_config, cleanup_collections):
    """Test whether a newer certified collection version can be installed.

    If the collection version was certified the latest version will be installed.
    """
    client = get_client(ansible_config("ansible_insights"))

    ansible_config("ansible_partner", namespace=USERNAME_PUBLISHER)
    collection = build_collection("skeleton", config={"namespace": USERNAME_PUBLISHER})
    ansible_galaxy(
        f"collection publish {collection.filename}",
        ansible_config=ansible_config("ansible_partner", namespace=USERNAME_PUBLISHER)
    )

    set_certification(client, collection)

    new_version = increment_version(collection.version)
    collection = build_collection(
        "skeleton",
        key=collection.key,
        config={"namespace": USERNAME_PUBLISHER, "version": new_version},
    )

    ansible_galaxy(
        f"collection publish {collection.filename}",
        ansible_config=ansible_config("ansible_partner", namespace=USERNAME_PUBLISHER)
    )

    set_certification(client, collection)

    ansible_config("ansible_partner")
    ansible_galaxy(
        f"collection install {collection.namespace}.{collection.name}",
        ansible_config=ansible_config("ansible_partner")
    )

    collection_path = get_collection_full_path(USERNAME_PUBLISHER, collection.name)
    with open(os.path.join(collection_path, "MANIFEST.json")) as manifest_json:
        data = json.load(manifest_json)
    assert data["collection_info"]["version"] == collection.version


@pytest.mark.cli
@pytest.mark.xfail
@pytest.mark.skip(reason="fails in ephemeral")
def test_publish_same_collection_version(ansible_config):
    """Test whether same collection version can be published."""
    ansible_config("ansible_partner", namespace=USERNAME_PUBLISHER)
    collection = build_collection("skeleton", config={"namespace": USERNAME_PUBLISHER})
    ansible_galaxy(
        f"collection publish {collection.filename}",
        ansible_config=ansible_config("ansible_partner", namespace=USERNAME_PUBLISHER)
    )
    p = ansible_galaxy(
        f"collection publish {collection.filename}",
        check_retcode=1,
        ansible_config=ansible_config("ansible_partner", namespace=USERNAME_PUBLISHER)
    )
    assert "Artifact already exists" in str(p.stderr)


@pytest.mark.cli
@pytest.mark.skip(reason="fails in ephemeral")
def test_publish_and_install_by_self(ansible_config, published, cleanup_collections):
    """A publishing user has the permission to install an uncertified version of their
    own collection.
    """

    ansible_config("ansible_partner")
    ansible_galaxy(
        f"collection install {published.namespace}.{published.name}:{published.version}",
        ansible_config=ansible_config("ansible_partner")
    )


@pytest.mark.cli
@pytest.mark.cloud_only
@pytest.mark.skip(reason="fails in ephemeral")
def test_publish_and_expect_uncertified_hidden(ansible_config, published, cleanup_collections):
    """A discovering/consumer user has the permission to download a specific version of an
    uncertified collection, but not an unspecified version range.
    """

    ansible_config("ansible_user")
    ansible_galaxy(
        f"collection install {published.namespace}.{published.name}", check_retcode=1,
        ansible_config=ansible_config("ansible_user")
    )
    ansible_galaxy(
        f"collection install {published.namespace}.{published.name}:1.0.0",
        ansible_config=ansible_config("ansible_user")
    )


@pytest.mark.cli
@pytest.mark.cloud_only
@pytest.mark.skip(reason="fails in ephemeral")
def test_certification_endpoint(ansible_config, artifact):
    """Certification makes a collection installable in a version range by a consumer-level
    user.
    """
    config = ansible_config("ansible_partner", namespace=artifact.namespace)
    p = run(
        f"ansible-galaxy collection publish {artifact.filename} -vvv --server=automation_hub"
        " --ignore-certs",
        shell=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    assert p.returncode == 0

    config = ansible_config("ansible_insights")
    client = get_client(config)

    url = f"v3/collections/{artifact.namespace}/{artifact.name}/versions/1.0.0/"
    with pytest.raises(CapturingGalaxyError) as excinfo:
        with patch("ansible.galaxy.api.GalaxyError", CapturingGalaxyError):
            client(url)
    assert "404" in str(excinfo.value)

    # assert details["certification"] == "needs_review"

    set_certification(client, artifact)

    url = f"v3/collections/{artifact.namespace}/{artifact.name}/versions/1.0.0/"
    details = client(url)
    assert details["certification"] == "certified", details

    config = ansible_config("ansible_partner")
    p = ansible_galaxy(
        f"collection install {artifact.namespace}.{artifact.name}:1.0.0",
        ansible_config=ansible_config("ansible_partner")
    )
    assert p.returncode == 0
