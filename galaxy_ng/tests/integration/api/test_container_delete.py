import subprocess
import pytest
from ..utils import get_client


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

    # View content before deleting
    assert len(content_list["results"]) > 0

    # Delete repository, contents, and artifacts
    delete_response = client(f"{api_prefix}/v3/"
                             "plugin/execution-environments/repositories/alpine/", method='DELETE')
    assert delete_response.status_code == 200

    # Ensure content list is empty
    assert len(content_list["results"]) == 0
