import requests
import subprocess

from .utils import (
    API_ROOT,
    ADMIN_USER,
    ADMIN_TOKEN,
    assert_pass,
    del_collection,
    del_namespace,
    gen_string,
    gen_namespace,
    reset_remote
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
