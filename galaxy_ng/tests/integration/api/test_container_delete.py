import subprocess
import pytest
from ..utils import get_client, wait_for_task
from ansible.galaxy.api import GalaxyError


@pytest.mark.standalone_only
def test_delete_ee_and_content(ansible_config):
    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")

    # Pull alpine image
    subprocess.check_call(["docker", "pull", "alpine"])
    # Tag the image
    subprocess.check_call(["docker", "tag", "alpine", "localhost:5001/alpine:latest"])

    # Login to local registy with tls verify disabled
    subprocess.check_call(["docker", "login", "-u", "admin", "-p", "admin", "localhost:5001"])

    # Push image to local registry
    subprocess.check_call(["docker", "push", "localhost:5001/alpine:latest"])

    # Get an API client running with admin user credentials
    client = get_client(
        config=ansible_config("admin"),
        request_token=True,
    )
    api_prefix = client.config.get("api_prefix").rstrip("/")

    # Go to the container distribution list and select the distribution via the base path.
    distro_response = client(
        f"{api_prefix}/pulp/api/v3/distributions/"
        "container/container/?base_path=alpine",
    )
    assert distro_response["results"][0]["base_path"] == 'alpine'

    # Grab the repository href from the json and make get request
    repo_href = (distro_response["results"][0]["repository"]).replace("/api/automation-hub", "")
    repo_response = client(f"{api_prefix}{repo_href}")

    # Grab <latest_version_href> field from this Container Push Repo Instance
    latest_version = repo_response["latest_version_href"]

    # Filter List Content List by the latest version found above
    content_list = client(
        f"{api_prefix}/pulp/api/v3/content/?repository_version={latest_version}",
    )

    # Check content before deleting
    assert len(content_list["results"]) > 0

    # Delete repository, contents, and artifacts
    delete_response = client(f"{api_prefix}/v3/"
                             "plugin/execution-environments/repositories/alpine/", method='DELETE')
    resp = wait_for_task(client, delete_response, timeout=10000)
    assert resp["state"] == "completed"

    # Ensure content list is empty by checking each content href
    content_hrefs = [item["pulp_href"] for item in content_list["results"]]

    for item in content_hrefs:
        failed = None
        try:
            client(f"{api_prefix}{item}")
            failed = False
        except GalaxyError as ge:
            if ge.http_code in [403, 404]:
                failed = True
            else:
                raise Exception(ge)

        assert failed


@pytest.mark.standalone_only
def test_shared_content_is_not_deleted(ansible_config):
    # Pull alpine image
    subprocess.check_call(["docker", "pull", "alpine"])

    # Tag the image
    subprocess.check_call(["docker", "tag", "alpine", "localhost:5001/alpine1:latest"])

    # Login to local registy with tls verify disabled
    subprocess.check_call(["docker", "login", "-u", "admin", "-p", "admin", "localhost:5001"])

    # Push image to local registry
    subprocess.check_call(["docker", "push", "localhost:5001/alpine1:latest"])

    # Copy 'alpine1' and rename to 'alpine2'
    subprocess.check_call(["docker", "tag", "alpine", "localhost:5001/alpine2:latest"])
    subprocess.check_call(["docker", "push", "localhost:5001/alpine2:latest"])

    # Get an API client running with admin user credentials
    client = get_client(
        config=ansible_config("admin"),
        request_token=True,
    )
    api_prefix = client.config.get("api_prefix").rstrip("/")

    # Select the distribution for alpine1 and alpine2.
    distro_response1 = client(
        f"{api_prefix}/pulp/api/v3/distributions/"
        "container/container/?base_path=alpine1",
    )
    distro_response2 = client(
        f"{api_prefix}/pulp/api/v3/distributions/"
        "container/container/?base_path=alpine2",
    )
    assert distro_response1["results"][0]["base_path"] == 'alpine1'
    assert distro_response2["results"][0]["base_path"] == 'alpine2'

    # Grab the repository href from the json and make get request
    repo_href_1 = (distro_response1["results"][0]["repository"]).replace("/api/automation-hub", "")
    repo_href_2 = (distro_response2["results"][0]["repository"]).replace("/api/automation-hub", "")
    repo_response_1 = client(f"{api_prefix}{repo_href_1}")
    repo_response_2 = client(f"{api_prefix}{repo_href_2}")

    # Grab <latest_version_href> field from this Container Push Repo Instance
    latest_version_1 = repo_response_1["latest_version_href"]
    latest_version_2 = repo_response_2["latest_version_href"]

    # Filter List Content List by the latest version found above
    content_list_1 = client(
        f"{api_prefix}/pulp/api/v3/content/?repository_version={latest_version_1}",
    )
    content_list_2 = client(
        f"{api_prefix}/pulp/api/v3/content/?repository_version={latest_version_2}",
    )

    # Check that content exists and is identical before deleting
    assert len(content_list_1["results"]) > 0
    assert len(content_list_2["results"]) > 0
    assert content_list_1 == content_list_2

    # Delete repository, contents, and artifacts for alpine1, NOT alpine2
    delete_response = client(f"{api_prefix}/v3/"
                             "plugin/execution-environments/repositories/alpine1/", method='DELETE')
    resp = wait_for_task(client, delete_response, timeout=10000)
    assert resp["state"] == "completed"

    # Ensure content hrefs from alpine1 still exists
    content_hrefs = [item["pulp_href"] for item in content_list_1["results"]]

    for item in content_hrefs:
        success = None
        try:
            client(item)
            success = True
        except GalaxyError as ge:
            if ge.http_code in [403, 404]:
                success = False
            else:
                raise Exception(ge)

        assert success
