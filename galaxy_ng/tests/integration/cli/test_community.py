"""test_community.py - Tests related to the community featureset.
"""

import os
import tempfile
import pytest
import subprocess

from ..utils import (
    ansible_galaxy,
    SocialGithubClient
)

from ..utils.legacy import clean_all_roles, cleanup_social_user


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_community
def test_import_role_as_owner(ansible_config):
    """ Tests role import workflow with a social auth user and anonymous install """

    # https://github.com/jctannerTEST/role1

    github_user = "jctannerTEST"
    github_repo = "role1"
    role_name = "role1"
    qs = f'v1/roles/?github_user={github_user}&name={role_name}'

    cfg = ansible_config(github_user)
    client = SocialGithubClient(config=cfg)
    client.login()
    token = client.get_hub_token()
    assert token is not None

    # cleanup the role if it exists
    resp = client.get(qs)
    ds = resp.json()
    if ds['count'] > 0:
        role = ds['results'][0]
        role_id = role['id']
        role_url = f'v1/roles/{role_id}/'
        resp = client.delete(role_url)
        assert resp.status_code == 204

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

    # validate it shows up
    resp = client.get(qs)
    assert resp.status_code == 200

    # validate the serializer
    ds = resp.json()
    role_id = ds['results'][0]['id']

    assert ds['count'] == 1
    role = ds['results'][0]
    assert role['name'] == role_name
    assert role['github_user'] == github_user
    assert role['github_repo'] == github_repo
    assert role['github_branch'] is not None
    assert role['commit'] is not None
    assert len(role['summary_fields']['versions']) == 1

    # validate the versions url
    versions_url = f'v1/roles/{role_id}/versions/'
    versions_resp = client.get(versions_url)
    assert versions_resp.status_code == 200
    versions = versions_resp.json()
    assert versions['results'][0]['version'] == \
        role['summary_fields']['versions'][0]['version']

    # validate the content url
    content_url = f'v1/roles/{role_id}/content/'
    content_resp = client.get(content_url)
    assert content_resp.status_code == 200
    content = content_resp.json()
    assert 'readme' in content
    assert 'readme_html' in content
    assert '<h1>role1</h1>' in content['readme_html']

    # validate cli search
    cfg = ansible_config('anonymous_user')
    search_pid = ansible_galaxy(
        f"role search --author={github_user} {role_name}",
        ansible_config=cfg,
        token=token,
        force_token=True,
        cleanup=False,
        check_retcode=False
    )
    # https://github.com/ansible/ansible/issues/78516
    # assert search_pid.returncode == 0
    assert f'{github_user}.{role_name}' in search_pid.stdout.decode('utf-8')

    # validate install command
    with tempfile.TemporaryDirectory() as roles_path:
        cfg = ansible_config('anonymous_user')
        install_pid = ansible_galaxy(
            f"role install -p {roles_path} {github_user}.{role_name}",
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


@pytest.mark.deployment_community
def test_import_role_as_not_owner(ansible_config):
    """ Tests role import workflow with non-owner """

    # https://github.com/jctannerTEST/role1

    importer = 'github_user_1'
    github_user = "jctannerTEST"
    github_repo = "role1"
    role_name = "role1"
    qs = f'v1/roles/?github_user={github_user}&name={role_name}'

    cfg = ansible_config(github_user)
    client = SocialGithubClient(config=cfg)
    client.login()
    token = client.get_hub_token()
    assert token is not None

    # cleanup the role if it exists
    resp = client.get(qs)
    ds = resp.json()
    if ds['count'] > 0:
        role = ds['results'][0]
        role_id = role['id']
        role_url = f'v1/roles/{role_id}/'
        resp = client.delete(role_url)
        assert resp.status_code == 204

    # Run the import as someone other than the owner
    cfg = ansible_config(importer)
    client = SocialGithubClient(config=cfg)
    client.login()
    token = client.get_hub_token()
    import_pid = ansible_galaxy(
        f"role import {github_user} {github_repo}",
        ansible_config=cfg,
        token=token,
        force_token=True,
        cleanup=False,
        check_retcode=False
    )
    assert import_pid.returncode == 1

    # validate it does not show up
    resp = client.get(qs)
    assert resp.status_code == 200
    ds = resp.json()
    assert ds.get('count') == 0


@pytest.mark.deployment_community
def test_import_role_fields(ansible_config):
    """Test role serializer fields after import with galaxy-importer>=0.4.11."""

    github_user = "jctannerTEST"
    github_repo = "role1"
    role_name = "role1"
    role_url = f"v1/roles/?github_user={github_user}&name={role_name}"

    # Cleanup all roles.
    clean_all_roles(ansible_config)

    config = ansible_config(github_user)
    client = SocialGithubClient(config=config)
    client.login()
    token = client.get_hub_token()
    assert token is not None

    import_pid = ansible_galaxy(
        f"role import {github_user} {github_repo}",
        ansible_config=config,
        token=token,
        force_token=True,
        cleanup=False,
        check_retcode=False
    )
    assert import_pid.returncode == 0

    result = client.get(role_url).json()["results"][0]

    for field in [
        "commit", "created", "description", "download_count", "github_branch", "github_repo",
        "github_user", "id", "modified", "name", "summary_fields", "upstream_id", "username"
    ]:
        assert field in result

    summary_fields = result["summary_fields"]
    assert summary_fields["dependencies"] == list()
    assert summary_fields["namespace"]["name"] == "jctannerTEST"
    assert summary_fields["provider_namespace"]["name"] == "jctannertest"
    assert summary_fields["repository"]["name"] == "role1"
    assert summary_fields["tags"] == list()

    assert len(summary_fields["versions"]) == 1
    for field in [
        "active", "commit_date", "commit_sha", "created", "download_url",
        "modified", "name", "release_date", "url", "version"
    ]:
        assert field in summary_fields["versions"][0]

    # Cleanup all roles.
    clean_all_roles(ansible_config)


@pytest.mark.deployment_community
def test_delete_role_as_not_owner(ansible_config):
    """ Tests role delete with non-owner """

    # https://github.com/jctannerTEST/role1

    deleter = 'github_user_1'
    github_user = "jctannerTEST"
    github_repo = "role1"
    role_name = "role1"
    qs = f'v1/roles/?github_user={github_user}&name={role_name}'

    cleanup_social_user(deleter, ansible_config)
    cleanup_social_user(github_user, ansible_config)
    cleanup_social_user(github_user.lower(), ansible_config)

    cfg = ansible_config(github_user)
    client = SocialGithubClient(config=cfg)
    client.login()
    token = client.get_hub_token()
    assert token is not None

    '''
    # cleanup the role if it exists
    resp = client.get(qs)
    ds = resp.json()
    if ds['count'] > 0:
        role = ds['results'][0]
        role_id = role['id']
        role_url = f'v1/roles/{role_id}/'
        resp = client.delete(role_url)
        assert resp.status_code == 200
    '''

    # Run the import as the owner
    cfg = ansible_config(github_user)
    client = SocialGithubClient(config=cfg)
    client.login()
    token = client.get_hub_token()
    import_pid = ansible_galaxy(
        f"role import {github_user} {github_repo}",
        ansible_config=cfg,
        token=token,
        force_token=True,
        cleanup=False,
        check_retcode=False
    )
    assert import_pid.returncode == 0

    cfg = ansible_config(deleter)
    client = SocialGithubClient(config=cfg)
    client.login()
    token = client.get_hub_token()
    assert token is not None

    # cleanup the role if it exists
    resp = client.get(qs)
    ds = resp.json()
    if ds['count'] > 0:
        role = ds['results'][0]
        role_id = role['id']
        role_url = f'v1/roles/{role_id}/'
        resp = client.delete(role_url)
        assert resp.status_code == 403


@pytest.mark.deployment_community
def test_delete_namespace_deletes_roles(ansible_config):
    """ Tests deleting namespace also deletes roles """

    # https://github.com/jctannerTEST/role1

    github_user = "jctannerTEST"
    github_repo = "role1"
    role_name = "role1"
    qs = f'v1/roles/?github_user={github_user}&name={role_name}'

    cfg = ansible_config(github_user)
    client = SocialGithubClient(config=cfg)
    client.login()
    token = client.get_hub_token()
    assert token is not None

    # cleanup the role if it exists
    resp = client.get(qs)
    ds = resp.json()
    if ds['count'] > 0:
        role = ds['results'][0]
        role_id = role['id']
        role_url = f'v1/roles/{role_id}/'
        resp = client.delete(role_url)
        assert resp.status_code == 204

    # Run the import as the owner
    import_pid = ansible_galaxy(
        f"role import {github_user} {github_repo}",
        ansible_config=cfg,
        token=token,
        force_token=True,
        cleanup=False,
        check_retcode=False
    )
    assert import_pid.returncode == 0

    # ensure the role exists
    resp = client.get(qs)
    ds = resp.json()
    assert ds['count'] == 1

    # delete the namespace
    res = client.get(f"v1/namespaces/?name={cfg['username']}")
    ns_id = res.json()['results'][0]['id']
    ns_url = f"v1/namespaces/{ns_id}/"
    dres = client.delete(ns_url)
    assert dres.status_code == 204

    # check if role still exists
    resp = client.get(qs)
    ds = resp.json()
    assert ds['count'] == 0


@pytest.mark.deployment_community
def test_delete_role_with_cli(ansible_config):
    """ Tests role delete with CLI """

    # https://github.com/jctannerTEST/role1

    github_user = "jctannerTEST"
    github_repo = "role1"
    role_name = "role1"

    # pre-clean the user, the namespace and the role
    cleanup_social_user(github_user, ansible_config)

    # Run the import as the owner
    cfg = ansible_config(github_user)
    client = SocialGithubClient(config=cfg)
    client.login()
    token = client.get_hub_token()
    import_pid = ansible_galaxy(
        f"role import {github_user} {github_repo}",
        ansible_config=cfg,
        token=token,
        force_token=True,
        cleanup=False,
        check_retcode=False
    )
    assert import_pid.returncode == 0

    # check namespace owners ...
    ns_resp = client.get(f'v1/namespaces/?name={github_user}')
    ns_ds = ns_resp.json()
    ns_owners = [x['username'] for x in ns_ds['results'][0]['summary_fields']['owners']]
    assert ns_owners == [github_user]

    # validate delete command
    url = client.baseurl.replace('/api/', '')
    cmd = (
        'ansible-galaxy role delete'
        + ' -vvvv'
        + f' --server={url}'
        + f' --token={token}'
        + f' {github_user}'
        + f' {role_name}'
    )
    delete_pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # FIXME: for some reason, returncode is 1 even if it runs correctly and role is deleted
    # assert delete_pid.returncode == 0 #, delete_pid.stderr.decode('utf-8')
    assert "Role jctannerTEST.role1 deleted" in delete_pid.stdout.decode('utf-8')


@pytest.mark.deployment_community
def test_delete_missing_role_with_cli(ansible_config):
    """ Tests missing role delete with CLI """

    # https://github.com/jctannerTEST/role1

    github_user = "jctannerTEST"
    github_repo = "CANTFINDMEANYWHERE"

    # pre-clean the user, the namespace and the role
    cleanup_social_user(github_user, ansible_config)

    cfg = ansible_config(github_user)
    client = SocialGithubClient(config=cfg)
    client.login()
    token = client.get_hub_token()

    # validate delete command
    url = client.baseurl.replace('/api/', '')
    cmd = (
        'ansible-galaxy role delete'
        + ' -vvvv'
        + f' --server={url}'
        + f' --token={token}'
        + f' {github_user}'
        + f' {github_repo}'
    )
    delete_pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # FIXME: should return 1?
    # assert delete_pid.returncode == 0 # , delete_pid.stderr.decode('utf-8')

    stdout = delete_pid.stdout.decode('utf-8')
    expected_msg = 'not found. Maybe it was deleted'
    assert expected_msg in stdout, stdout
