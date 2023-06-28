import pytest
from ..utils import get_client, uuid4, wait_for_task


@pytest.fixture
def admin_client(ansible_config):
    return get_client(
        config=ansible_config("admin"),
        request_token=True,
    )


@pytest.fixture
def basic_user_client(ansible_config):
    return get_client(
        config=ansible_config("basic_user"),
        request_token=True,
    )


@pytest.fixture
def repo_factory(admin_client):

    def _repo_factory(repo_url, private=False):
        return admin_client(
            repo_url,
            args={
                "name": f"repo-test-{uuid4()}",
                "description": f"repo-test-{uuid4()}",
                "private": private,
            },
            method="POST",
        )

    return _repo_factory


@pytest.fixture
def distro_factory(admin_client):

    def _distro_factory(repo, distro_url):
        distro_task = admin_client(
            distro_url,
            args={
                "base_path": f"dist-test-{uuid4()}",
                "name": f"dist-test-{uuid4()}",
                "repository": repo,
            },
            method="POST",
        )
        task_results = wait_for_task(api_client=admin_client, resp=distro_task)
        return admin_client(f"{task_results['created_resources'][0]}")

    return _distro_factory


@pytest.mark.deployment_standalone
@pytest.mark.private_repos
@pytest.mark.min_hub_version("4.7dev")
def test_private_repositories(admin_client, basic_user_client, repo_factory):
    api_prefix = admin_client.config.get("api_prefix").rstrip("/")
    url = f"{api_prefix}/pulp/api/v3/repositories/ansible/ansible/"

    # Create private & public repos
    private_repo_resp = repo_factory(url, True)
    assert private_repo_resp["private"] is True
    public_repo_resp = repo_factory(url)
    assert public_repo_resp["private"] is False

    admin_repo_list_resp = admin_client(url, method="GET")
    basic_user_repo_list_resp = basic_user_client(url, method="GET")

    assert private_repo_resp in admin_repo_list_resp["results"]
    assert public_repo_resp in admin_repo_list_resp["results"]
    assert private_repo_resp not in basic_user_repo_list_resp["results"]
    assert public_repo_resp in basic_user_repo_list_resp["results"]

    # Cleanup
    admin_client(f'{private_repo_resp["pulp_href"]}', method="DELETE")
    admin_client(f'{public_repo_resp["pulp_href"]}', method="DELETE")


@pytest.mark.deployment_standalone
@pytest.mark.private_repos
@pytest.mark.min_hub_version("4.7dev")
def test_distributions_with_private_repositories(
    admin_client, basic_user_client, distro_factory, repo_factory
):
    api_prefix = admin_client.config.get("api_prefix").rstrip("/")
    repo_url = f"{api_prefix}/pulp/api/v3/repositories/ansible/ansible/"
    distro_url = f"{api_prefix}/pulp/api/v3/distributions/ansible/ansible/"

    # Create a private & public repos
    private_repo_resp = repo_factory(repo_url, True)
    assert private_repo_resp["private"] is True
    public_repo_resp = repo_factory(repo_url)
    assert public_repo_resp["private"] is False

    # Create a private & public
    private_distro_resp = distro_factory(private_repo_resp["pulp_href"], distro_url)
    public_distro_resp = distro_factory(public_repo_resp["pulp_href"], distro_url)

    admin_distro_list_resp = admin_client(distro_url, method="GET")
    basic_user_distro_list_resp = basic_user_client(distro_url, method="GET")

    assert private_distro_resp in admin_distro_list_resp["results"]
    assert public_distro_resp in admin_distro_list_resp["results"]

    assert private_distro_resp not in basic_user_distro_list_resp["results"]
    assert public_distro_resp in basic_user_distro_list_resp["results"]

    # Cleanup
    admin_client(f'{private_distro_resp["pulp_href"]}', method="DELETE")
    admin_client(f'{public_distro_resp["pulp_href"]}', method="DELETE")
    admin_client(f'{private_repo_resp["pulp_href"]}', method="DELETE")
    admin_client(f'{public_repo_resp["pulp_href"]}', method="DELETE")
