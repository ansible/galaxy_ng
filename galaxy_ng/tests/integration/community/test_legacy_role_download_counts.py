"""test_community.py - Tests related to the community featureset.
"""

import os
import tempfile
import pytest

import concurrent.futures

from ..utils import (
    ansible_galaxy,
    SocialGithubClient
)


pytestmark = pytest.mark.qa  # noqa: F821


def clean_role(client, namespace, name):

    qs = f'v1/roles/?github_user={namespace}&name={name}'

    # cleanup the role if it exists
    resp = client.get(qs)
    ds = resp.json()
    if ds['count'] > 0:
        role = ds['results'][0]
        role_id = role['id']
        role_url = f'v1/roles/{role_id}/'
        resp = client.delete(role_url)
        assert resp.status_code == 204


def import_role(client, cfg, token, github_user, github_repo):
    # Run the import
    import_pid = ansible_galaxy(
        f"role import {github_user} {github_repo}",
        ansible_config=cfg,
        token=token,
        force_token=True,
        cleanup=False,
        check_retcode=False
    )
    assert import_pid.returncode == 0


@pytest.mark.deployment_community
def test_legacy_role_download_counter_via_cli(ansible_config):
    """ Tests role import workflow with a social auth user and anonymous install """

    # https://github.com/jctannerTEST/role1
    github_user = "jctannerTEST"
    github_repo = "role1"
    role_name = "role1"

    # this query should -not- increment the download counter
    qs = f'v1/roles/?github_user={github_user}&name={role_name}'

    cfg = ansible_config(github_user)
    client = SocialGithubClient(config=cfg)
    client.login()
    token = client.get_hub_token()
    assert token is not None

    clean_role(client, github_user, role_name)
    import_role(client, cfg, token, github_user, github_repo)

    # validate it shows up
    resp = client.get(qs)
    assert resp.status_code == 200

    # validate the serializer
    ds = resp.json()
    assert ds['count'] == 1
    role = ds['results'][0]

    # should start with zero downloads
    assert role['download_count'] == 0

    # validate install command
    for x in range(0, 5):
        with tempfile.TemporaryDirectory() as roles_path:
            cfg = ansible_config('anonymous_user')
            install_pid = ansible_galaxy(
                f"role install --force -p {roles_path} {github_user}.{role_name}",
                ansible_config=cfg,
                token=token,
                force_token=True,
                cleanup=False,
                check_retcode=False
            )
            assert install_pid.returncode == 0
            expected_path = os.path.join(roles_path, f'{github_user}.{role_name}')
            assert os.path.exists(expected_path)
            meta_yaml = os.path.join(expected_path, 'meta', 'main.yml')
            assert os.path.exists(meta_yaml)

    # check the new count ...
    resp = client.get(qs)
    assert resp.status_code == 200
    ds = resp.json()
    role = ds['results'][0]
    assert role['download_count'] == 5


@pytest.mark.deployment_community
def test_legacy_role_download_counter_concurrency(ansible_config):
    """ Tests role import workflow with a social auth user and anonymous install """

    # https://github.com/jctannerTEST/role1
    github_user = "jctannerTEST"
    github_repo = "role1"
    role_name = "role1"

    # this query should -not- increment the download counter
    qs = f'v1/roles/?github_user={github_user}&name={role_name}'

    # this DOES increment the counter ...
    qs_incrementer = f'v1/roles/?owner__username={github_user}&name={role_name}'

    cfg = ansible_config(github_user)
    client = SocialGithubClient(config=cfg)
    client.login()
    token = client.get_hub_token()
    assert token is not None

    clean_role(client, github_user, role_name)
    import_role(client, cfg, token, github_user, github_repo)

    # validate it shows up
    resp = client.get(qs)
    assert resp.status_code == 200

    # validate the serializer
    ds = resp.json()
    assert ds['count'] == 1
    role = ds['results'][0]

    # should start with zero downloads
    assert role['download_count'] == 0

    def fake_install_role(number):
        print(f'FAKE INSTALL ROLE ... {number}')
        client.get(qs_incrementer)

    # fetch the correct url N times at once validate no race conditions ...
    total = 20
    total_threads = total
    args_list = [[x] for x in range(0, total)]
    kwargs_list = [{} for x in range(0, total)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=total_threads) as executor:

        future_to_args_kwargs = {
            executor.submit(fake_install_role, *args, **kwargs): (args, kwargs)
            for args, kwargs in zip(args_list, kwargs_list)
        }

        for future in concurrent.futures.as_completed(future_to_args_kwargs):
            args, kwargs = future_to_args_kwargs[future]
            future.result()

    # make sure it incremented with no race conditions ...
    assert client.get(qs).json()['results'][0]['download_count'] == total
