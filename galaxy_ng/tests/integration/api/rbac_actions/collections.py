import requests
import subprocess

from .utils import (
    API_ROOT,
    PULP_API_ROOT,
    SERVER,
    ADMIN_USER,
    ADMIN_PASSWORD,
    ADMIN_TOKEN,
    ADMIN_CREDENTIALS,
    assert_pass,
    del_collection,
    del_namespace,
    gen_string,
    gen_namespace,
    reset_remote,
    create_ansible_repo,
    create_ansible_distro,
    create_ansible_remote
)

from galaxy_ng.tests.integration.utils import build_collection


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

    name = gen_string()

    artifact = build_collection(
        name=name,
        namespace=extra['collection'].get_namespace()["name"]
    )

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
        API_ROOT,
        artifact.filename
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    del_collection(name, extra['collection'].get_namespace()["name"])

    if expect_pass:
        assert proc.returncode == 0
    else:
        assert proc.returncode != 0


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


def add_ansible_repository(user, password, expect_pass, extra):
    create_ansible_repo(user['username'], password, expect_pass)


def modify_ansible_repository(user, password, expect_pass, extra):
    ansible_repo = create_ansible_repo(ADMIN_USER, ADMIN_PASSWORD, True).json()
    base_ansible_repo = create_ansible_repo(ADMIN_USER, ADMIN_PASSWORD, True).json()

    base_ansible_repo_version = f"{base_ansible_repo['pulp_href']}versions/0/"

    response = requests.post(
        f"{SERVER}{ansible_repo['pulp_href']}modify/",
        json={"base_version": base_ansible_repo_version},
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def rebuild_metadata_ansible_repository(user, password, expect_pass, extra):
    ansible_repo = create_ansible_repo(ADMIN_USER, ADMIN_PASSWORD, True).json()

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
    ansible_repo = create_ansible_repo(ADMIN_USER, ADMIN_PASSWORD, True).json()

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
    ansible_repo = create_ansible_repo(ADMIN_USER, ADMIN_PASSWORD, True).json()
    remote_response = create_ansible_remote(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.post(
        f"{SERVER}{ansible_repo['pulp_href']}sync/",
        json={"remote": remote_response["pulp_href"]},
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def delete_ansible_repository(user, password, expect_pass, extra):
    repo = create_ansible_repo(ADMIN_USER, ADMIN_PASSWORD, True)

    response = requests.delete(
        f"{SERVER}{repo.json()['pulp_href']}",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def view_ansible_repository_version(user, password, expect_pass, extra):
    repo = create_ansible_repo(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.get(
        f"{SERVER}{repo['versions_href']}",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


# FIXME: pulp_1   | TypeError: rebuild_metadata() got an unexpected keyword argument 'repository_pk'
def rebuild_metadata_ansible_repository_version(user, password, expect_pass, extra):
    repo = create_ansible_repo(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.post(
        f"{SERVER}{repo['versions_href']}0/rebuild_metadata/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def repair_ansible_repository_version(user, password, expect_pass, extra):
    repo = create_ansible_repo(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.post(
        f"{SERVER}{repo['versions_href']}0/repair/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def delete_ansible_repository_version(user, password, expect_pass, extra):
    repo = create_ansible_repo(ADMIN_USER, ADMIN_PASSWORD, True).json()

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
            "name": f"foobar-{gen_string()}",
            "base_path": f"foobar-{gen_string()}"
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def change_ansible_distribution(user, password, expect_pass, extra):
    ansible_distro = create_ansible_distro(ADMIN_USER, ADMIN_PASSWORD, True).json()

    response = requests.put(
        f"{SERVER}{ansible_distro['pulp_href']}",
        {
            "name": f"bazqux-{gen_string()}",
            "base_path": f"bazqux-{gen_string()}"
        },
        # auth=ADMIN_CREDENTIALS,
        auth=(user['username'], password),
    )

    assert_pass(expect_pass, response.status_code, 202, 403)


def delete_ansible_distribution(user, password, expect_pass, extra):
    ansible_distro = create_ansible_distro(ADMIN_USER, ADMIN_PASSWORD, True).json()

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
    create_ansible_remote(user['username'], password, expect_pass)


def change_ansible_remote(user, password, expect_pass, extra):
    ansible_remote = create_ansible_remote(ADMIN_USER, ADMIN_PASSWORD, True).json()
    response = requests.put(
        f"{SERVER}{ansible_remote['pulp_href']}",
        json={
            "name": f"bazqux-{gen_string()}",
            "url": "baz.qux/api/"
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def delete_ansible_remote(user, password, expect_pass, extra):
    ansible_remote = create_ansible_remote(ADMIN_USER, ADMIN_PASSWORD, True).json()
    response = requests.delete(
        f"{SERVER}{ansible_remote['pulp_href']}",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)
