import requests
import subprocess

from .utils import (
    API_ROOT,
    PULP_API_ROOT,
    SERVER,
    ADMIN_USER,
    ADMIN_PASSWORD,
    ADMIN_CREDENTIALS,
    assert_pass,
    del_namespace,
    gen_string,
    gen_namespace,
    reset_remote,
    wait_for_task,
    del_collection,
    build_collection,
    ADMIN_TOKEN,
    add_role_common,
    remove_role_common,
    list_roles_common,
    InvalidResponse,
)

import logging

logger = logging.getLogger()


def _create_ansible_repo_common(user, password, expect_pass):
    response = requests.post(
        f"{PULP_API_ROOT}repositories/ansible/ansible/",
        json={
            "pulp_labels": {},
            "name": f"repo_ansible-{gen_string()}",
            "description": "foobar",
            "gpgkey": "foobar"
        },
        auth=(user, password),
    )
    assert_pass(expect_pass, response.status_code, 201, 403)
    return response


def _create_ansible_distro_common(user, password, expect_pass):
    task_response = requests.post(
        f"{PULP_API_ROOT}distributions/ansible/ansible/",
        {
            "name": f"dist-test-{gen_string()}",
            "base_path": f"dist-test-{gen_string()}"
        },
        auth=(user, password),
    )

    assert_pass(expect_pass, task_response.status_code, 202, 403)

    finished_task_response = wait_for_task(task_response)
    assert_pass(expect_pass, finished_task_response.status_code, 200, 403)

    created_resources = finished_task_response.json()['created_resources'][0]
    response = requests.get(
        f"{SERVER}{created_resources}",
        auth=(user, password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)
    return response


def _create_ansible_remote_common(user, password, expect_pass):
    response = requests.post(
        f"{PULP_API_ROOT}remotes/ansible/collection/",
        json={
            "name": f"foobar-{gen_string()}",
            "url": "foo.bar/api/"
        },
        auth=(user, password),
    )
    assert_pass(expect_pass, response.status_code, 201, 403)
    return response


def _upload_collection_common(user, password, expect_pass, extra, base_path=None):
    name = gen_string()

    artifact = build_collection(
        name=name,
        namespace=extra['collection'].get_namespace()["name"]
    )

    server = API_ROOT
    if base_path:
        server = API_ROOT + f"content/{base_path}/"

    # Don't reset the admin user's token, or all the other tests
    # will break
    if user['username'] == ADMIN_USER:
        token = ADMIN_TOKEN
    else:
        token = requests.post(
            f'{API_ROOT}v3/auth/token/',
            auth=(user['username'], password),
        ).json()['token'] or None

    cmd = [
        "ansible-galaxy",
        "collection",
        "publish",
        "--api-key",
        token,
        "--server",
        server,
        artifact.filename
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    del_collection(name, extra['collection'].get_namespace()["name"], repo=base_path)

    if expect_pass:
        assert proc.returncode == 0
    else:
        assert proc.returncode != 0


def create_collection_namespace(user, password, expect_pass, extra):
    ns = gen_string()

    response = requests.post(
        f"{API_ROOT}_ui/v1/namespaces/",
        json={
            "name": ns,
            "groups": [],
        },
        auth=(user['username'], password),
    )

    del_namespace(ns)

    assert_pass(expect_pass, response.status_code, 201, 403)
    return response.json()


def change_collection_namespace(user, password, expect_pass, extra):
    ns = extra['collection'].get_namespace()

    response = requests.put(
        f"{API_ROOT}_ui/v1/namespaces/{ns['name']}/",
        json={**ns, "description": "foo"},
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def delete_collection_namespace(user, password, expect_pass, extra):
    name = gen_string()

    gen_namespace(name)

    response = requests.delete(
        f"{API_ROOT}_ui/v1/namespaces/{name}/",
        auth=(user['username'], password),
    )

    del_namespace(name)

    assert_pass(expect_pass, response.status_code, 204, 403)


def upload_collection_to_namespace(user, password, expect_pass, extra):
    _upload_collection_common(user, password, expect_pass, extra)


def upload_collection_to_custom_staging_repo(user, password, expect_pass, extra):
    _upload_collection_common(
        user,
        password,
        expect_pass,
        extra,
        extra["custom_staging_repo"].get_distro()["base_path"]
    )


def upload_collection_to_custom_repo(user, password, expect_pass, extra):
    _upload_collection_common(
        user,
        password,
        expect_pass,
        extra,
        extra["custom_repo"].get_distro()["base_path"]
    )


def upload_collection_to_other_pipeline_repo(user, password, expect_pass, extra):
    _upload_collection_common(
        user,
        password,
        expect_pass,
        extra,
        "rejected"
    )


def delete_collection(user, password, expect_pass, extra):
    collection = extra['collection'].get_collection()

    ns = collection['namespace']
    name = collection['name']

    response = requests.delete(
        f"{API_ROOT}v3/plugin/ansible/content/staging/collections/index/{ns}/{name}/",
        auth=(user['username'], password),
    )

    assert_pass(expect_pass, response.status_code, 202, 403)


def configure_collection_sync(user, password, expect_pass, extra):
    remote = reset_remote()

    remote['password'] = "foobar"

    response = requests.put(
        f"{API_ROOT}content/{remote['name']}/v3/sync/config/",
        json=remote,
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def launch_collection_sync(user, password, expect_pass, extra):
    # call get_remote to reset object
    remote = reset_remote()

    response = requests.post(
        f"{API_ROOT}content/{remote['name']}/v3/sync/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def view_sync_configuration(user, password, expect_pass, extra):
    remote = reset_remote()

    response = requests.get(
        f"{API_ROOT}content/{remote['name']}/v3/sync/config/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def approve_collections(user, password, expect_pass, extra):
    collection = extra['collection'].get_collection()
    response = requests.post(
        (
            f"{API_ROOT}v3/collections/{collection['namespace']}"
            f"/{collection['name']}/versions/{collection['version']}"
            "/move/staging/published/"
        ),
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def reject_collections(user, password, expect_pass, extra):
    collection = extra['collection'].get_collection()
    response = requests.post(
        (
            f"{API_ROOT}v3/collections/{collection['namespace']}"
            f"/{collection['name']}/versions/{collection['version']}"
            "/move/staging/rejected/"
        ),
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def deprecate_collections(user, password, expect_pass, extra):
    collection = extra['collection'].get_collection()
    response = requests.patch(
        (
            f"{API_ROOT}v3/plugin/ansible/content/staging/collections"
            f"/index/{collection['namespace']}/{collection['name']}/"
        ),
        json={"deprecated": True},
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def undeprecate_collections(user, password, expect_pass, extra):
    collection = extra['collection'].get_collection()

    response = requests.patch(
        (
            f"{API_ROOT}v3/plugin/ansible/content/staging/collections"
            f"/index/{collection['namespace']}/{collection['name']}/"
        ),
        json={"deprecated": False},
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def view_ansible_repository(user, password, expect_pass, extra):
    response = requests.get(
        f"{PULP_API_ROOT}repositories/ansible/ansible",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def collection_repo_list_roles(user, password, expect_pass, extra):
    pulp_href = extra["custom_repo"].get_repo()['pulp_href']
    list_roles_common(user, password, expect_pass, pulp_href)


def collection_repo_add_role(user, password, expect_pass, extra):
    pulp_href = extra["custom_repo"].get_repo()['pulp_href']
    add_role_common(user, password, expect_pass, pulp_href, "galaxy.ansible_repository_owner")


def collection_repo_remove_role(user, password, expect_pass, extra):
    pulp_href = extra["custom_repo"].get_repo()['pulp_href']
    remove_role_common(user, password, expect_pass, pulp_href, "galaxy.ansible_repository_owner")


def add_ansible_repository(user, password, expect_pass, extra):
    _create_ansible_repo_common(user['username'], password, expect_pass)


def modify_ansible_repository(user, password, expect_pass, extra):
    ansible_repo = _create_ansible_repo_common(ADMIN_USER, ADMIN_PASSWORD, True).json()
    base_ansible_repo = _create_ansible_repo_common(ADMIN_USER, ADMIN_PASSWORD, True).json()

    base_ansible_repo_version = f"{base_ansible_repo['pulp_href']}versions/0/"

    response = requests.post(
        f"{SERVER}{ansible_repo['pulp_href']}modify/",
        json={"base_version": base_ansible_repo_version},
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def rebuild_metadata_ansible_repository(user, password, expect_pass, extra):
    ansible_repo = _create_ansible_repo_common(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.post(
        f"{SERVER}{ansible_repo['pulp_href']}rebuild_metadata/",
        json={
            "namespace": "foo",
            "name": "bar",
            "version": "123"
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def sign_ansible_repository(user, password, expect_pass, extra):
    ansible_repo = _create_ansible_repo_common(ADMIN_USER, ADMIN_PASSWORD, True).json()

    sign_serv_response = requests.get(
        f"{PULP_API_ROOT}signing-services/?name=ansible-default",
        auth=ADMIN_CREDENTIALS,
    )
    assert_pass(True, sign_serv_response.status_code, 200, 403)

    sign_serv_href = sign_serv_response.json()['results'][0]['pulp_href']
    response = requests.post(
        f"{SERVER}{ansible_repo['pulp_href']}sign/",
        json={
            "content_units": ["*"],
            "signing_service": sign_serv_href
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def sync_ansible_repository(user, password, expect_pass, extra):
    ansible_repo = _create_ansible_repo_common(ADMIN_USER, ADMIN_PASSWORD, True).json()
    remote_response = _create_ansible_remote_common(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.post(
        f"{SERVER}{ansible_repo['pulp_href']}sync/",
        json={"remote": remote_response["pulp_href"]},
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def delete_ansible_repository(user, password, expect_pass, extra):
    repo = _create_ansible_repo_common(ADMIN_USER, ADMIN_PASSWORD, True)

    response = requests.delete(
        f"{SERVER}{repo.json()['pulp_href']}",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def view_ansible_repository_version(user, password, expect_pass, extra):
    repo_href = extra["custom_repo"].get_repo()["pulp_href"]
    response = requests.get(
        f"{SERVER}{repo_href}",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def rebuild_metadata_ansible_repository_version(user, password, expect_pass, extra):
    ansible_repo = _create_ansible_repo_common(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.post(
        f"{SERVER}{ansible_repo['latest_version_href']}rebuild_metadata/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def repair_ansible_repository_version(user, password, expect_pass, extra):
    repo = _create_ansible_repo_common(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.post(
        f"{SERVER}{repo['versions_href']}0/repair/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def delete_ansible_repository_version(user, password, expect_pass, extra):
    repo = _create_ansible_repo_common(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.delete(
        f"{SERVER}{repo['versions_href']}0/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def view_ansible_distribution(user, password, expect_pass, extra):
    response = requests.get(
        f"{PULP_API_ROOT}distributions/ansible/ansible/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def add_ansible_distribution(user, password, expect_pass, extra):
    response = requests.post(
        f"{PULP_API_ROOT}distributions/ansible/ansible/",
        {
            "name": f"dist-test-{gen_string()}",
            "base_path": f"dist-test{gen_string()}"
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def change_ansible_distribution(user, password, expect_pass, extra):
    ansible_distro = _create_ansible_distro_common(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.put(
        f"{SERVER}{ansible_distro['pulp_href']}",
        {
            "name": f"dist-test-{gen_string()}",
            "base_path": f"dist-test-{gen_string()}"
        },
        # auth=ADMIN_CREDENTIALS,
        auth=(user['username'], password),
    )

    assert_pass(expect_pass, response.status_code, 202, 403)


def delete_ansible_distribution(user, password, expect_pass, extra):
    ansible_distro = _create_ansible_distro_common(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.delete(
        f"{SERVER}{ansible_distro['pulp_href']}",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def view_ansible_remote(user, password, expect_pass, extra):
    response = requests.get(
        f"{PULP_API_ROOT}remotes/ansible/collection/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def add_ansible_remote(user, password, expect_pass, extra):
    _create_ansible_remote_common(user['username'], password, expect_pass)


def change_ansible_remote(user, password, expect_pass, extra):
    ansible_remote = _create_ansible_remote_common(ADMIN_USER, ADMIN_PASSWORD, True).json()
    response = requests.put(
        f"{SERVER}{ansible_remote['pulp_href']}",
        json={
            "name": f"dist-test-{gen_string()}",
            "url": "baz.qux/api/"
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def delete_ansible_remote(user, password, expect_pass, extra):
    ansible_remote = _create_ansible_remote_common(ADMIN_USER, ADMIN_PASSWORD, True).json()
    response = requests.delete(
        f"{SERVER}{ansible_remote['pulp_href']}",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def collection_remote_list_roles(user, password, expect_pass, extra):
    pulp_href = requests.get(
        f"{PULP_API_ROOT}remotes/ansible/collection/?name=community",
        auth=ADMIN_CREDENTIALS
    ).json()["results"][0]["pulp_href"]
    list_roles_common(user, password, expect_pass, pulp_href)


def collection_remote_add_role(user, password, expect_pass, extra):
    pulp_href = requests.get(
        f"{PULP_API_ROOT}remotes/ansible/collection/?name=community",
        auth=ADMIN_CREDENTIALS
    ).json()["results"][0]["pulp_href"]
    add_role_common(user, password, expect_pass, pulp_href, "galaxy.collection_remote_owner")


def collection_remote_remove_role(user, password, expect_pass, extra):
    pulp_href = requests.get(
        f"{PULP_API_ROOT}remotes/ansible/collection/?name=community",
        auth=ADMIN_CREDENTIALS
    ).json()["results"][0]["pulp_href"]
    remove_role_common(user, password, expect_pass, pulp_href, "galaxy.collection_remote_owner")


def _private_repo_assert_pass(response, results, expect_pass):
    if response.status_code != 200:
        raise InvalidResponse("200 expected from this API")

    if expect_pass:
        assert len(results) == 1
    else:
        assert len(results) == 0


def private_repo_list(user, password, expect_pass, extra):
    repo = extra["private_repo"].get_repo()
    response = requests.get(
        f"{PULP_API_ROOT}repositories/ansible/ansible/?name={repo['name']}",
        auth=(user['username'], password),
    )

    _private_repo_assert_pass(response, response.json()["results"], expect_pass)


def private_distro_list(user, password, expect_pass, extra):
    distro = extra["private_repo"].get_distro()
    response = requests.get(
        f"{PULP_API_ROOT}distributions/ansible/ansible/?name={distro['name']}",
        auth=(user['username'], password),
    )

    _private_repo_assert_pass(response, response.json()["results"], expect_pass)


def private_collection_version_list(user, password, expect_pass, extra):
    repo = extra["private_repo"].get_repo()
    response = requests.get(
        f"{API_ROOT}v3/plugin/ansible/search/collection-versions/?repository_name={repo['name']}",
        auth=(user['username'], password),
    )

    _private_repo_assert_pass(response, response.json()["data"], expect_pass)


def view_private_repository_version(user, password, expect_pass, extra):
    repo = extra["private_repo"].get_repo()
    response = requests.get(
        f"{SERVER}{repo['versions_href']}",
        auth=(user['username'], password),
    )

    assert_pass(expect_pass, response.status_code, 200, 403)


def private_repo_v3(user, password, expect_pass, extra):
    distro = extra["private_repo"].get_distro()

    response = requests.get(
        f"{API_ROOT}content/{distro['base_path']}/v3/collections",
        allow_redirects=True,
        auth=(user['username'], password),
    )

    assert_pass(expect_pass, response.status_code, 200, 403)


# TODO move logic to ReusableCollection._reset_collection()
def _reset_collection_repo(cv_pulp_href, repo, staging_repo):
    requests.post(
        f"{SERVER}{repo['pulp_href']}move_collection_version/",
        json={
            "collection_versions": [f"{cv_pulp_href}"],
            "destination_repositories": [f"{staging_repo['pulp_href']}"]
        },
        auth=ADMIN_CREDENTIALS,
    )


def copy_collection_version(user, password, expect_pass, extra):
    repo = extra["custom_repo"].get_repo()
    collection = extra['collection'].get_collection()
    collection_version_response = requests.get(
        f"{PULP_API_ROOT}content/ansible/collection_versions/?name={collection['name']}",
        auth=ADMIN_CREDENTIALS,
    ).json()
    ds = collection_version_response["results"]
    assert len(ds) == 1
    cv_pulp_href = ds[0]['pulp_href']

    staging_repo_resp = requests.get(
        f"{PULP_API_ROOT}repositories/ansible/ansible/?name=staging",
        auth=ADMIN_CREDENTIALS,
    ).json()
    assert len(staging_repo_resp['results']) == 1
    staging_repo = staging_repo_resp["results"][0]

    response = requests.post(
        f"{SERVER}{staging_repo['pulp_href']}copy_collection_version/",
        json={
            "collection_versions": [f"{cv_pulp_href}"],
            "destination_repositories": [f"{repo['pulp_href']}"]
        },
        auth=(user['username'], password),
    )

    if response.status_code == 202:
        _reset_collection_repo(cv_pulp_href, repo, staging_repo)

    assert_pass(expect_pass, response.status_code, 202, 403)


def copy_multiple_collection_version(user, password, expect_pass, extra):
    repo1 = extra["custom_repo"].get_repo()
    repo2 = extra["custom_repo"].get_repo()
    collection = extra['collection'].get_collection()
    collection_version_response = requests.get(
        f"{PULP_API_ROOT}content/ansible/collection_versions/?name={collection['name']}",
        auth=ADMIN_CREDENTIALS,
    ).json()
    ds = collection_version_response["results"]
    assert len(ds) == 1
    cv_pulp_href = ds[0]['pulp_href']

    staging_repo_resp = requests.get(
        f"{PULP_API_ROOT}repositories/ansible/ansible/?name=staging",
        auth=ADMIN_CREDENTIALS,
    ).json()
    assert len(staging_repo_resp['results']) == 1
    staging_repo = staging_repo_resp["results"][0]

    response = requests.post(
        f"{SERVER}{staging_repo['pulp_href']}copy_collection_version/",
        json={
            "collection_versions": [f"{cv_pulp_href}"],
            "destination_repositories": [f"{repo1['pulp_href']}", f"{repo2['pulp_href']}"]
        },
        auth=(user['username'], password),
    )

    assert_pass(expect_pass, response.status_code, 202, 403)


def move_collection_version(user, password, expect_pass, extra):
    repo = extra["custom_repo"].get_repo()
    collection = extra['collection'].get_collection()
    collection_version_response = requests.get(
        f"{PULP_API_ROOT}content/ansible/collection_versions/?name={collection['name']}",
        auth=ADMIN_CREDENTIALS,
    ).json()
    ds = collection_version_response["results"]
    assert len(ds) == 1
    cv_pulp_href = ds[0]['pulp_href']

    staging_repo_resp = requests.get(
        f"{PULP_API_ROOT}repositories/ansible/ansible/?name=staging",
        auth=ADMIN_CREDENTIALS,
    ).json()
    assert len(staging_repo_resp['results']) == 1
    staging_repo = staging_repo_resp["results"][0]

    response = requests.post(
        f"{SERVER}{staging_repo['pulp_href']}move_collection_version/",
        json={
            "collection_versions": [f"{cv_pulp_href}"],
            "destination_repositories": [f"{repo['pulp_href']}"]
        },
        auth=(user['username'], password),
    )

    if response.status_code == 202:
        _reset_collection_repo(cv_pulp_href, repo, staging_repo)

    assert_pass(expect_pass, response.status_code, 202, 403)
