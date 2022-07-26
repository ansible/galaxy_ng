import requests
from subprocess import Popen, PIPE, STDOUT

from .utils import (
    ADMIN_CREDENTIALS,
    API_ROOT,
    NAMESPACE,
    PASSWORD,
    assert_pass,
    collection_namespace_exists,
    create_user,
    create_group_with_user_and_role,
    del_collection,
    object_user_exists,
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


# NEEDS TO BE REFACTORED
def change_collection_namespace_object(role, expect_pass, extra):
    username = f'{NAMESPACE}_user_ns_object'
    # remove user object if it exists
    if object_user_exists():
        user = object_user_exists()
        requests.delete(
            f"{API_ROOT}_ui/v1/users/{user['id']}/",
            auth=ADMIN_CREDENTIALS,
        )
    # create clean user object
    user = create_user(username, PASSWORD)
    group = create_group_with_user_and_role(user, role, group=f'{NAMESPACE}_group_ns_obj')
    # remove namespace object if it exists
    if collection_namespace_exists(f"{NAMESPACE}_col_ns_obj"):
        response = collection_namespace_exists(f"{NAMESPACE}_col_ns_obj")
        requests.delete(
            f"{API_ROOT}_ui/v1/namespaces/{response['name']}/",
            auth=ADMIN_CREDENTIALS,
        )
    # create clean namespace object
    create_response = requests.post(
        f"{API_ROOT}_ui/v1/namespaces/",
        json={
            "name": f"{NAMESPACE}_col_ns_obj",
            "groups": [{
                "id": group["id"],
                "name": group["name"],
                "object_roles": [role],
            }],
        },
        auth=ADMIN_CREDENTIALS,
    ).json()
    if 'errors' not in create_response.keys():
        response = requests.put(
            f"{API_ROOT}_ui/v1/my-namespaces/{create_response['name']}/",
            json={
                "name": f"{create_response['name']}",
                "groups": [create_response['groups']],
                "description": "Updated description"
            },
            auth=(user['username'], PASSWORD),
        )
        assert_pass(expect_pass, response.status_code, 200, 403)
    else:  # no permissions related to object
        assert not expect_pass and create_response['errors'][0]['status'] == 400
    # cleanup user, group, namespace
    requests.delete(f"{API_ROOT}_ui/v1/users/{user['id']}/", auth=ADMIN_CREDENTIALS)
    requests.delete(f"{API_ROOT}_ui/v1/groups/{group['id']}/", auth=ADMIN_CREDENTIALS)
    requests.delete(f"{API_ROOT}_ui/v1/namespaces/{NAMESPACE}_col_ns_obj/", auth=ADMIN_CREDENTIALS)


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
    proc = Popen(cmd, stdout=PIPE, stderr=STDOUT, encoding="utf-8")
    return_code = proc.wait()

    del_collection(name, extra['collection'].get_namespace()["name"])

    if expect_pass:
        assert return_code == 0
    else:
        assert return_code != 0


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
