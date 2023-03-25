import pytest
import subprocess
import tempfile

from ..utils import (
    AnsibleDistroAndRepo,
    get_client, gen_string,
    CollectionInspector,
    wait_for_all_tasks
)


def _upload_test_common(config, client, artifact, base_path, dest_base_path=None):
    if dest_base_path is None:
        dest_base_path = base_path

    cmd = [
        "ansible-galaxy",
        "collection",
        "publish",
        "--api-key",
        config["token"],
        "--server",
        config["url"] + f"content/{base_path}/",
        artifact.filename
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    assert proc.returncode == 0

    wait_for_all_tasks(client)

    collection_url = (
        f"/content/{dest_base_path}/v3/collections/"
        f"{artifact.namespace}/{artifact.name}/versions/1.0.0/"
    )

    collection_resp = client(collection_url)
    assert collection_resp["name"] == artifact.name

    # test download
    with tempfile.TemporaryDirectory() as dir:
        api_root = config["url"]
        filename = f"{artifact.namespace}-{artifact.name}-{artifact.version}.tar.gz"
        tarball_path = f"{dir}/{filename}"
        url = (
            f"{api_root}v3/plugin/ansible/content/"
            f"{dest_base_path}/collections/artifacts/{filename}"
        )

        cmd = [
            "curl",
            "--retry",
            "5",
            "-L",
            "-H",
            "'Content-Type: application/json'",
            "-u",
            f"{config['username']}:{config['password']}",
            "-o",
            tarball_path,
            url
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        returncode = proc.wait()
        assert returncode == 0

        # Extract tarball, verify information in manifest
        ci = CollectionInspector(tarball=tarball_path)
        assert ci.namespace == artifact.namespace
        assert ci.name == artifact.name
        assert ci.version == artifact.version


@pytest.mark.standalone_only
def test_publish_to_custom_staging_repo(ansible_config, artifact, settings):
    if settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL") is not True:
        pytest.skip("GALAXY_REQUIRE_CONTENT_APPROVAL must be true")
    config = ansible_config(profile="admin")
    client = get_client(
        config=config
    )

    repo = AnsibleDistroAndRepo(
        client,
        gen_string(),
        repo_body={"pulp_labels": {"pipeline": "staging"}}
    )

    _upload_test_common(config, client, artifact, repo.get_distro()["base_path"])


@pytest.mark.standalone_only
def test_publish_to_custom_repo(ansible_config, artifact, settings):
    if settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL") is not True:
        pytest.skip("GALAXY_REQUIRE_CONTENT_APPROVAL must be true")
    config = ansible_config(profile="admin")
    client = get_client(
        config=config
    )

    repo = AnsibleDistroAndRepo(
        client,
        gen_string(),
    )

    _upload_test_common(config, client, artifact, repo.get_distro()["base_path"])


@pytest.mark.standalone_only
@pytest.mark.auto_approve
def test_publish_and_auto_approve(ansible_config, artifact, settings):
    if settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_CONTENT_APPROVAL must be false")
    config = ansible_config(profile="admin")
    client = get_client(
        config=config
    )

    repo = AnsibleDistroAndRepo(
        client,
        gen_string(),
    )

    _upload_test_common(config, client, artifact, repo.get_distro()["base_path"], "published")

    cv = client(
        "/content/published/v3/collections/"
        f"{artifact.namespace}/{artifact.name}/versions/1.0.0/"

    )

    assert len(cv["signatures"]) >= 1


@pytest.mark.standalone_only
@pytest.mark.auto_approve
def test_auto_approve_muliple(ansible_config, artifact, settings):
    if settings.get("GALAXY_REQUIRE_CONTENT_APPROVAL"):
        pytest.skip("GALAXY_REQUIRE_CONTENT_APPROVAL must be false")
    config = ansible_config(profile="admin")
    client = get_client(
        config=config
    )
    custom_published_repo = AnsibleDistroAndRepo(
        client,
        gen_string(),
        repo_body={"pulp_labels": {"pipeline": "approved"}}
    )

    published = custom_published_repo.get_distro()["base_path"]

    _upload_test_common(config, client, artifact, "staging", published)

    cv = client(
        f"/content/{published}/v3/collections/"
        f"{artifact.namespace}/{artifact.name}/versions/1.0.0/"

    )

    assert len(cv["signatures"]) >= 1

    cv = client(
        f"/content/published/v3/collections/"
        f"{artifact.namespace}/{artifact.name}/versions/1.0.0/"

    )

    assert len(cv["signatures"]) >= 1
    assert cv["name"] == artifact.name
