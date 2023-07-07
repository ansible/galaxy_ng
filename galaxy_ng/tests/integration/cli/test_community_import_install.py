import os
import tempfile

import pytest

from ..utils import ansible_galaxy, get_client, SocialGithubClient
from ..utils.legacy import clean_all_roles, cleanup_social_user


@pytest.mark.deployment_community
def test_import_install_role_as_admin(ansible_config):
    """Tests installing a role that was imported by an owner that is
    not the same as the role's github_user."""

    # We will import jctannerTEST role1 as admin.
    github_user = "jctannerTEST"
    github_repo = "role1"
    role_name = "role1"
    role_url = f"v1/roles/?github_user={github_user}&name={role_name}"

    # Cleanup all roles.
    clean_all_roles(ansible_config)

    # Login as admin.
    admin_config = ansible_config("admin")
    admin_client = get_client(admin_config)
    token = admin_client.token
    assert token is not None

    # Import jctannerTEST role1 as admin.
    import_pid = ansible_galaxy(
        f"role import {github_user} {github_repo}",
        ansible_config=admin_config,
        token=token,
        cleanup=False,
        check_retcode=False
    )
    assert import_pid.returncode == 0

    # Ensure successful import.
    data = admin_client(role_url)
    assert data["count"] == 1
    assert data["results"][0]["github_user"] == github_user
    assert data["results"][0]["name"] == role_name

    # Use temporary directory for role installation.
    # Validate successful installation.
    with tempfile.TemporaryDirectory() as roles_path:
        install_pid = ansible_galaxy(
            f"role install -p {roles_path} {github_user}.{role_name}",
            ansible_config=admin_config,
            token=token,
            cleanup=False,
            check_retcode=False
        )
        assert install_pid.returncode == 0
        expected_path = os.path.join(roles_path, f"{github_user}.{role_name}")
        assert os.path.exists(expected_path)
        meta_yaml = os.path.join(expected_path, "meta", "main.yml")
        assert os.path.exists(meta_yaml)


@pytest.mark.deployment_community
def test_import_install_role_as_not_admin(ansible_config):
    """Tests installing a role that was imported by an owner that is
    not the same as the role's github_user."""

    # We will import jctannerTEST role1 as admin.
    github_user = "jctannerTEST"
    github_repo = "role1"
    role_name = "role1"
    role_url = f"v1/roles/?github_user={github_user}&name={role_name}"

    # Cleanup all roles.
    clean_all_roles(ansible_config)

    # Login as jctannerTEST.
    test_config = ansible_config(github_user)
    test_client = SocialGithubClient(config=test_config)
    test_client.login()
    token = test_client.get_hub_token()
    assert token is not None

    # Import jctannerTEST role1 as jctannerTEST.
    import_pid = ansible_galaxy(
        f"role import {github_user} {github_repo}",
        ansible_config=test_config,
        token=token,
        force_token=True,
        cleanup=False,
        check_retcode=False
    )
    assert import_pid.returncode == 0

    # Ensure successful import.
    response = test_client.get(role_url)
    response_json = response.json()
    assert response.status_code == 200
    assert response_json["count"] == 1
    assert response_json["results"][0]["github_user"] == github_user
    assert response_json["results"][0]["name"] == role_name

    # Use temporary directory for role installation.
    # Validate successful installation for jctannerTEST.
    with tempfile.TemporaryDirectory() as roles_path:
        install_pid = ansible_galaxy(
            f"role install -p {roles_path} {github_user}.{role_name}",
            ansible_config=test_config,
            token=token,
            force_token=True,
            cleanup=False,
            check_retcode=False
        )
        assert install_pid.returncode == 0
        expected_path = os.path.join(roles_path, f"{github_user}.{role_name}")
        assert os.path.exists(expected_path)
        meta_yaml = os.path.join(expected_path, "meta", "main.yml")
        assert os.path.exists(meta_yaml)

    # Login as github_user_1.
    user_1_config = ansible_config("github_user_1")
    user_1_client = SocialGithubClient(config=user_1_config)
    user_1_client.login()
    token = user_1_client.get_hub_token()
    assert token is not None

    # Use temporary directory for role installation.
    # Validate successful installation for github_user_1.
    with tempfile.TemporaryDirectory() as roles_path:
        install_pid = ansible_galaxy(
            f"role install -p {roles_path} {github_user}.{role_name}",
            ansible_config=user_1_config,
            token=token,
            force_token=True,
            cleanup=False,
            check_retcode=False
        )
        assert install_pid.returncode == 0
        expected_path = os.path.join(roles_path, f"{github_user}.{role_name}")
        assert os.path.exists(expected_path)
        meta_yaml = os.path.join(expected_path, "meta", "main.yml")
        assert os.path.exists(meta_yaml)


@pytest.mark.deployment_community
def test_import_owner_not_github_user(ansible_config):
    """Tests importing a role as an owner that is different from the GitHub user."""

    # We will import jctannerTEST role1 as github_user_1.
    github_user = "jctannerTEST"
    github_repo = "role1"
    role_name = "role1"
    namespace_url = "v1/namespaces/"
    me_url = "_ui/v1/me/"

    # Cleanup jctannerTEST.
    cleanup_social_user(github_user, ansible_config)

    # Login as jctannerTEST.
    test_config = ansible_config(github_user)
    test_client = SocialGithubClient(config=test_config)
    test_client.login()
    test_token = test_client.get_hub_token()
    assert test_token is not None

    # Login as github_user_1.
    gh1_config = ansible_config("github_user_1")
    gh1_client = SocialGithubClient(config=gh1_config)
    gh1_client.login()
    gh1_token = gh1_client.get_hub_token()
    assert gh1_token is not None

    # Create a jctannerTEST namespace with owner jctannerTEST.
    response = test_client.get(namespace_url + f"?name={github_user}")
    assert response.status_code == 200
    namespace_id = response.json()["results"][0]["id"]

    # Update owners to include github_user_1.
    response = test_client.get(me_url)
    assert response.status_code == 200
    test_id = response.json()["id"]
    response = gh1_client.get(me_url)
    assert response.status_code == 200
    gh1_id = response.json()["id"]
    updated_owners = {"owners": [{"id": test_id}, {"id": gh1_id}]}
    response = test_client.put(namespace_url + f"{namespace_id}/owners/", data=updated_owners)
    assert response.status_code == 200

    # Import jctanerTEST role1 as github_user_1.
    import_pid = ansible_galaxy(
        f"role import {github_user} {github_repo}",
        ansible_config=gh1_config,
        token=gh1_token,
        force_token=True,
        cleanup=False,
        check_retcode=False
    )
    assert import_pid.returncode == 0
    assert any(res["name"] == role_name for res in test_client.get("v1/roles/").json()["results"])

    # Ensure that the role is installable...
    with tempfile.TemporaryDirectory() as roles_path:
        install_pid = ansible_galaxy(
            f"role install -p {roles_path} {github_user}.{role_name}",
            ansible_config=gh1_config,
            token=gh1_token,
            force_token=True,
            cleanup=False,
            check_retcode=False
        )
        assert install_pid.returncode == 0
        expected_path = os.path.join(roles_path, f"{github_user}.{role_name}")
        assert os.path.exists(expected_path)
        meta_yaml = os.path.join(expected_path, "meta", "main.yml")
        assert os.path.exists(meta_yaml)
