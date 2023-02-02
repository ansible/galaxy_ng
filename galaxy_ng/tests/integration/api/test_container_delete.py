import requests
import subprocess


def delete_ee_and_content(user, password, ansible_config):
    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")

    # Pull alpine image
    subprocess.check_call(["podman", "pull", "alpine"])

    # Tag the image
    subprocess.check_call(["podman", "tag", "alpine", "localhost:5001/alpine:latest"])

    # Go to the container distribution list and select the distribution via the base path.
    distro_response = requests.get(
        f"{api_prefix}/api/automation-hub/pulp/api/v3/distributions/\
            container/container/?base_path=alpine",
        auth=(user['username'], password),
    )
    assert distro_response["results"][0]["base_path"] == 'alpine'

    # Grab the repository href from the json and make get request
    repo_href = distro_response["results"][0]["repository"]
    repo_response = requests.get(f"{api_prefix}{repo_href}")

    # Grab <latest_version_href> field from this Container Push Repo Instance
    latest_version = repo_response["latest_version_href"]

    # Filter List Content List by the latest version found above
    content_list = requests.get(
        f"{api_prefix}/api/automation-hub/pulp/api/v3/content/?repository_version={latest_version}",
        auth=(user['username'], password),
    )

    # View content before deleting
    assert content_list["results"].length > 0

    # Delete repository, contents, and artifacts
    delete_response = requests.delete(f"{api_prefix}/api/\
        automation-hub/v3/plugin/execution-environments/repositories/alpine/")
    assert delete_response.status_code == 200

    # Ensure content list is empty
    assert content_list["results"].length == 0
