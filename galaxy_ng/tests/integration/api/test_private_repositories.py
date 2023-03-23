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


@pytest.mark.standalone_only
def test_private_repositories(admin_client, basic_user_client):
    api_prefix = admin_client.config.get("api_prefix").rstrip("/")
    url = f"{api_prefix}/pulp/api/v3/repositories/ansible/ansible/"

    # Create private & public repos
    private_repo_resp = admin_client(
        url,
        args={
            "name": f"private_{uuid4()}",
            "description": f"private_{uuid4()}",
            "private": "True",
        },
        method="POST",
    )
    assert private_repo_resp["private"] is True
    public_repo_resp = admin_client(
        url,
        args={
            "name": f"public_{uuid4()}",
            "description": f"public_{uuid4()}",
        },
        method="POST",
    )
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


@pytest.mark.standalone_only
def test_distributions_with_private_repositories(admin_client, basic_user_client):
    api_prefix = admin_client.config.get("api_prefix").rstrip("/")
    repo_url = f"{api_prefix}/pulp/api/v3/repositories/ansible/ansible/"
    distro_url = f"{api_prefix}/pulp/api/v3/distributions/ansible/ansible/"

    # Create a private & public repos
    private_repo_resp = admin_client(
        repo_url,
        args={
            "name": f"private_{uuid4()}",
            "description": f"private_{uuid4()}",
            "private": "True",
        },
        method="POST",
    )
    assert private_repo_resp["private"] is True
    public_repo_resp = admin_client(
        repo_url,
        args={
            "name": f"public_{uuid4()}",
            "description": f"public_{uuid4()}",
        },
        method="POST",
    )
    assert public_repo_resp["private"] is False

    # Create a private & public & repo'less distros
    private_distro_task = admin_client(
        distro_url,
        args={
            "base_path": f"private_distro_{uuid4()}",
            "name": f"private_distro_{uuid4()}",
            "repository": private_repo_resp["pulp_href"],
        },
        method="POST",
    )
    private_task_results = wait_for_task(api_client=admin_client, resp=private_distro_task)
    private_distro_resp = admin_client(f"{private_task_results['created_resources'][0]}")

    public_distro_task = admin_client(
        distro_url,
        args={
            "base_path": f"public_distro_{uuid4()}",
            "name": f"public_distro_{uuid4()}",
            "repository": public_repo_resp["pulp_href"],
        },
        method="POST",
    )
    public_task_results = wait_for_task(api_client=admin_client, resp=public_distro_task)
    public_distro_resp = basic_user_client(f"{public_task_results['created_resources'][0]}")
    repoless_distro_task = admin_client(
        distro_url,
        args={
            "base_path": f"repoless_distro_{uuid4()}",
            "name": f"repoless_distro_{uuid4()}",
            "repository": "",
        },
        method="POST",
    )
    repoless_distro_task_results = wait_for_task(api_client=admin_client, resp=repoless_distro_task)
    repoless_distro_resp = basic_user_client(
        f"{repoless_distro_task_results['created_resources'][0]}"
    )

    admin_distro_list_resp = admin_client(distro_url, method="GET")
    basic_user_distro_list_resp = basic_user_client(distro_url, method="GET")

    assert private_distro_resp in admin_distro_list_resp["results"]
    assert public_distro_resp in admin_distro_list_resp["results"]
    assert repoless_distro_resp in admin_distro_list_resp["results"]

    assert private_distro_resp not in basic_user_distro_list_resp["results"]
    assert public_distro_resp in basic_user_distro_list_resp["results"]
    assert repoless_distro_resp in basic_user_distro_list_resp["results"]

    # Cleanup
    admin_client(f'{private_distro_resp["pulp_href"]}', method="DELETE")
    admin_client(f'{public_distro_resp["pulp_href"]}', method="DELETE")
    admin_client(f'{repoless_distro_resp["pulp_href"]}', method="DELETE")
    admin_client(f'{private_repo_resp["pulp_href"]}', method="DELETE")
    admin_client(f'{public_repo_resp["pulp_href"]}', method="DELETE")
