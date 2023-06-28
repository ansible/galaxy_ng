import pytest
from ..utils import get_client, iterate_all


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_repository_labels(ansible_config):
    # Get an API client running with admin user credentials
    client = get_client(
        config=ansible_config("admin"),
        request_token=True,
    )
    api_prefix = client.config.get("api_prefix").rstrip("/")

    labels = {
        "!hide_from_search": {"rh-certified", "validated", "published", "community"},
        "hide_from_search": {"staging", "rejected"},
        "pipeline": {"staging", "rejected", "published"},
        "pipeline=staging": {"staging"},
        "pipeline=rejected": {"rejected"},
        "pipeline=approved": {"published"},
    }

    for label in labels:
        url = api_prefix + "/pulp/api/v3/repositories/ansible/ansible/?pulp_label_select={}"
        repos = {
            resp["name"] for resp in iterate_all(
                client, url.format(label))
        }
        # now we have test cases that create multiple repos, we don't want
        # to take them into account in this test case
        repos_to_remove = []
        for repo in repos:
            if repo.startswith("repo-test-") or repo.startswith("repo_ansible-"):
                repos_to_remove.append(repo)
        for repo in repos_to_remove:
            repos.remove(repo)

        assert repos == labels[label]
