import subprocess

import pytest

from galaxykit.containers import get_container_distribution, delete_container
from galaxykit.utils import wait_for_task, GalaxyClientError

from ..utils.iqe_utils import pull_and_tag_test_image


# this is to be enabled when https://github.com/ansible/galaxy_ng/pull/1627
# is merged


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
@pytest.mark.skip(reason="fix this test")
def test_delete_ee_and_content(ansible_config, galaxy_client):
    config = ansible_config("admin")

    container_engine = config["container_engine"]
    container_registry = config["container_registry"]
    username = config['username']
    password = config['password']

    # Pull alpine image
    pull_and_tag_test_image(container_engine, container_registry)

    # Login to local registry with tls verify disabled
    cmd = [container_engine, "login", "-u", username, "-p",
           password, container_registry]
    if container_engine == 'podman':
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Push image to local registry
    cmd = [container_engine, "push", f"{container_registry}/alpine:latest"]
    if container_engine == 'podman':
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Get an API client running with admin user credentials
    gc = galaxy_client("admin")
    # Go to the container distribution list and select the distribution via the base path.
    distro_response = get_container_distribution(gc, "alpine")
    assert distro_response["results"][0]["base_path"] == 'alpine'

    # Grab the repository href from the json and make get request
    repo_response = gc.get(distro_response["results"][0]["repository"])

    # Grab <latest_version_href> field from this Container Push Repo Instance
    latest_version = repo_response["latest_version_href"]

    # Filter List Content List by the latest version found above
    content_list = gc.get(f"pulp/api/v3/content/?repository_version={latest_version}")

    # Check content before deleting
    assert len(content_list["results"]) > 0

    # Delete repository, contents, and artifacts
    delete_response = delete_container(gc, "alpine")
    resp = wait_for_task(gc, delete_response.json(), timeout=10000)
    assert resp["state"] == "completed"

    # Ensure content list is empty by checking each content href
    content_hrefs = [item["pulp_href"] for item in content_list["results"]]
    # FIXME: all items are found. Check it.
    for item in content_hrefs:
        failed = None
        try:
            gc.get(item)
            failed = False
        except GalaxyClientError as ge:
            if ge.response.status_code in [403, 404]:
                failed = True
            else:
                raise Exception(ge)

        assert failed


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_shared_content_is_not_deleted(ansible_config, galaxy_client):
    gc = galaxy_client("admin")
    config = ansible_config("admin")
    container_engine = config["container_engine"]
    container_registry = config["container_registry"]
    username = config['username']
    password = config['password']

    # FIXME - these settings are wrong for dab_jwt ...
    if 'jwtproxy' in gc.galaxy_root:
        container_registry = gc.galaxy_root.split('/')[2]
        password = 'redhat'

    # Pull alpine image
    image = pull_and_tag_test_image(container_engine, container_registry, "alpine1:latest")
    # Login to local registry with tls verify disabled
    cmd = [container_engine, "login", "-u", username, "-p",
           password, container_registry]
    if container_engine == 'podman':
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Push image to local registry
    cmd = [container_engine, "push", f"{container_registry}/alpine1:latest"]

    if container_engine == 'podman':
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Copy 'alpine1' and rename to 'alpine2'
    subprocess.check_call([container_engine, "tag", image,
                           f"{container_registry}/alpine2:latest"])
    cmd = [container_engine, "push", f"{container_registry}/alpine2:latest"]
    if container_engine == 'podman':
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Select the distribution for alpine1 and alpine2.
    distro_response1 = get_container_distribution(gc, "alpine1")
    distro_response2 = get_container_distribution(gc, "alpine2")
    assert distro_response1["results"][0]["base_path"] == 'alpine1'
    assert distro_response2["results"][0]["base_path"] == 'alpine2'

    # Grab the repository href from the json and make get request
    repo_response_1 = gc.get(distro_response1["results"][0]["repository"])
    repo_response_2 = gc.get(distro_response2["results"][0]["repository"])

    # Grab <latest_version_href> field from this Container Push Repo Instance
    latest_version_1 = repo_response_1["latest_version_href"]
    latest_version_2 = repo_response_2["latest_version_href"]

    # Filter List Content List by the latest version found above
    content_list_1 = gc.get(f"pulp/api/v3/content/?repository_version={latest_version_1}")
    content_list_2 = gc.get(f"pulp/api/v3/content/?repository_version={latest_version_2}")

    # Check that content exists and is identical before deleting
    assert len(content_list_1["results"]) > 0
    assert len(content_list_2["results"]) > 0
    assert content_list_1 == content_list_2

    # Delete repository, contents, and artifacts for alpine1, NOT alpine2
    delete_response = delete_container(gc, "alpine1")
    resp = wait_for_task(gc, delete_response.json(), timeout=10000)
    assert resp["state"] == "completed"

    # Ensure content hrefs from alpine1 still exists
    content_hrefs = [item["pulp_href"] for item in content_list_1["results"]]

    for item in content_hrefs:
        success = None
        try:
            gc.get(item)
            success = True
        except GalaxyClientError as ge:
            if ge.response.status_code in [403, 404]:
                success = False
            else:
                raise Exception(ge)

        assert success

    delete_response = delete_container(gc, "alpine2")
    resp = wait_for_task(gc, delete_response.json(), timeout=10000)
    assert resp["state"] == "completed"
