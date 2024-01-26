import pytest

from galaxykit.utils import wait_for_task
from ..utils import uuid4


@pytest.fixture
def repo_factory(galaxy_client):
    gc = galaxy_client("admin")
    def _repo_factory(repo_url, private=False):
        return gc.post(
            repo_url,
            body={
                "name": f"repo-test-{uuid4()}",
                "description": f"repo-test-{uuid4()}",
                "private": private,
            }
        )

    return _repo_factory


@pytest.fixture
def distro_factory(galaxy_client):
    gc = galaxy_client("admin")
    def _distro_factory(repo, distro_url):
        distro_task = gc.post(
            distro_url,
            body={
                "base_path": f"dist-test-{uuid4()}",
                "name": f"dist-test-{uuid4()}",
                "repository": repo,
            }
        )
        task_results = wait_for_task(gc, distro_task)
        return gc.get(f"{task_results['created_resources'][0]}")

    return _distro_factory


@pytest.mark.deployment_standalone
@pytest.mark.private_repos
@pytest.mark.min_hub_version("4.7dev")
def test_private_repositories(repo_factory, galaxy_client):
    gc_admin = galaxy_client("admin", ignore_cache=True)
    gc_basic = galaxy_client("basic_user", ignore_cache=True)
    url = "pulp/api/v3/repositories/ansible/ansible/"

    # Create private & public repos
    private_repo_resp = repo_factory(url, True)
    assert private_repo_resp["private"] is True
    public_repo_resp = repo_factory(url)
    assert public_repo_resp["private"] is False

    admin_repo_list_resp = gc_admin.get(url)
    basic_user_repo_list_resp = gc_basic.get(url)

    assert private_repo_resp in admin_repo_list_resp["results"]
    assert public_repo_resp in admin_repo_list_resp["results"]
    assert private_repo_resp not in basic_user_repo_list_resp["results"]
    assert public_repo_resp in basic_user_repo_list_resp["results"]

    # Cleanup
    gc_admin.delete(f'{private_repo_resp["pulp_href"]}')
    gc_admin.delete(f'{public_repo_resp["pulp_href"]}')


@pytest.mark.deployment_standalone
@pytest.mark.private_repos
@pytest.mark.min_hub_version("4.7dev")
def test_distributions_with_private_repositories(
    galaxy_client, distro_factory, repo_factory
):
    gc_admin = galaxy_client("admin", ignore_cache=True)
    gc_basic = galaxy_client("basic_user", ignore_cache=True)

    repo_url = "pulp/api/v3/repositories/ansible/ansible/"
    distro_url = "pulp/api/v3/distributions/ansible/ansible/"

    # Create a private & public repos
    private_repo_resp = repo_factory(repo_url, True)
    assert private_repo_resp["private"] is True
    public_repo_resp = repo_factory(repo_url)
    assert public_repo_resp["private"] is False

    # Create a private & public
    private_distro_resp = distro_factory(private_repo_resp["pulp_href"], distro_url)
    public_distro_resp = distro_factory(public_repo_resp["pulp_href"], distro_url)

    admin_distro_list_resp = gc_admin.get(distro_url)
    basic_user_distro_list_resp = gc_basic.get(distro_url)

    assert private_distro_resp in admin_distro_list_resp["results"]
    assert public_distro_resp in admin_distro_list_resp["results"]

    assert private_distro_resp not in basic_user_distro_list_resp["results"]
    assert public_distro_resp in basic_user_distro_list_resp["results"]

    # Cleanup
    gc_admin.delete(f'{private_distro_resp["pulp_href"]}')
    gc_admin.delete(f'{public_distro_resp["pulp_href"]}')
    gc_admin.delete(f'{private_repo_resp["pulp_href"]}')
    gc_admin.delete(f'{public_repo_resp["pulp_href"]}')
