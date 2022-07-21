import os
import requests
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT
from time import sleep

from .utils import (
    ADMIN_CREDENTIALS,
    ADMIN_PASSWORD,
    ADMIN_USER,
    API_ROOT,
    NAMESPACE,
    PASSWORD,
    assert_pass,
    cleanup_foo_collection,
    collection_namespace_exists,
    create_user,
    create_group_with_user_and_role,
    foo_collection_exists,
    foo_namespace_exists,
    object_user_exists,
)

requirements_file = "collections:\n  - name: newswangerd.collection_demo\n    version: 1.0.11\n    source: https://galaxy.ansible.com"  # noqa: 501


def create_collection_namespace(user, password, expect_pass):
    if collection_namespace_exists():
        response = collection_namespace_exists()
        requests.delete(
            f"{API_ROOT}_ui/v1/namespaces/{response['name']}/",
            auth=ADMIN_CREDENTIALS,
        )
    response = requests.post(
        f"{API_ROOT}_ui/v1/namespaces/",
        json={
            "name": f"{NAMESPACE}_col_ns",
            "groups": [],
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 201, 403)


def change_collection_namespace(user, password, expect_pass):
    if collection_namespace_exists():
        ns_response = collection_namespace_exists()
    else:
        ns_response = create_collection_namespace(ADMIN_USER, ADMIN_PASSWORD, True)
        while not collection_namespace_exists():
            sleep(5)
    response = requests.put(
        f"{API_ROOT}_ui/v1/namespaces/{ns_response['name']}/",
        json={
            "name": ns_response["name"],
            "groups": ns_response["groups"],
            "description": "Praise the description!",
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def change_collection_namespace_object(role, expect_pass):
    username = f'{NAMESPACE}_user_ns_object'
    # remove user object if it exists
    if object_user_exists(username):
        user = object_user_exists(username)
        requests.delete(
            f"{API_ROOT}_ui/v1/users/{user['id']}/",
            auth=ADMIN_CREDENTIALS,
        )
    # create clean user object
    user = create_user(f'{NAMESPACE}_user_ns_object', PASSWORD)
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
        response = requests.post(
            f"{API_ROOT}_ui/v1/namespaces/",
            json={
                "name": f"{create_response['name']}",
                "groups": [create_response['groups']],
                "description": "Updated description"
            },
            auth=(user['username'], PASSWORD),
        )
        if expect_pass:
            assert response.status_code == 200
        else:
            assert response.status_code == 403
    else:  # no permissions related to object
        assert not expect_pass and create_response['errors'][0]['status'] == 400
    # cleanup user, group, namespace
    requests.delete(f"{API_ROOT}_ui/v1/users/{user['id']}/", auth=ADMIN_CREDENTIALS)
    requests.delete(f"{API_ROOT}_ui/v1/groups/{group['id']}/", auth=ADMIN_CREDENTIALS)
    requests.delete(f"{API_ROOT}_ui/v1/namespaces/{NAMESPACE}_col_ns_obj/", auth=ADMIN_CREDENTIALS)


def delete_collection_namespace(user, password, expect_pass):
    if collection_namespace_exists():
        ns_response = collection_namespace_exists()
    else:
        ns_response = create_collection_namespace(ADMIN_USER, ADMIN_PASSWORD, True)
    namespace_name = ns_response["name"]
    response = requests.delete(
        f"{API_ROOT}_ui/v1/namespaces/{namespace_name}/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 204, 403)


def upload_collection_to_namespace(user, password, expect_pass):
    cleanup_foo_collection()
    # get auth token for user
    token = requests.post(
        'http://localhost:5001/api/automation-hub/v3/auth/token/',
        auth=(user['username'], password),
    ).json()['token'] or None
    response = requests.post(
        f"{API_ROOT}_ui/v1/namespaces/",
        json={
            "name": "foo",
            "groups": [],
        },
        auth=ADMIN_CREDENTIALS,
    )
    if token is not None and response.status_code == 201:
        cmd = [
            "ansible-galaxy",
            "collection",
            "publish",
            "--api-key",
            token,
            "--server",
            API_ROOT,
            f"{os.path.dirname(__file__)}/foo-bar-1.0.0.tar.gz"
        ]
        proc = Popen(cmd, stdout=PIPE, stderr=STDOUT, encoding="utf-8")
        return_code = proc.wait()
        if expect_pass:
            assert return_code == 0
        else:
            assert return_code != 0


def delete_collection(user, password, expect_pass):
    if not foo_collection_exists('staging'):
        upload_collection_to_namespace(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.delete(
        f"{API_ROOT}v3/plugin/ansible/content/staging/collections/index/foo/bar/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def configure_collection_sync(user, password, expect_pass):
    response = requests.put(
        f"{API_ROOT}content/community/v3/sync/config/",
        json={
            "url": "https://galaxy.ansible.com/api/",
            "auth_url": None,
            "token": None,
            "policy": "immediate",
            "requirements_file": requirements_file,
            "created_at": str(datetime.now()),
            "updated_at": str(datetime.now()),
            "username": None,
            "password": None,
            "tls_validation": False,
            "client_key": None,
            "client_cert": None,
            "download_concurrency": 10,
            "proxy_url": None,
            "proxy_username": None,
            "proxy_password": None,
            "rate_limit": 8,
            "signed_only": False,
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def launch_collection_sync(user, password, expect_pass):
    configure_collection_sync(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.post(
        f"{API_ROOT}content/community/v3/sync/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def view_sync_configuration(user, password, expect_pass):
    response = requests.get(
        f"{API_ROOT}content/community/v3/sync/config/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def approve_collections(user, password, expect_pass):
    if foo_collection_exists('published'):
        cleanup_foo_collection()
    if not foo_collection_exists('staging'):
        upload_collection_to_namespace(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.post(
        f"{API_ROOT}v3/collections/foo/bar/versions/1.0.0/move/staging/published/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def reject_collections(user, password, expect_pass):
    if foo_collection_exists('rejected'):
        cleanup_foo_collection()
    if not foo_collection_exists('staging'):
        upload_collection_to_namespace(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.post(
        f"{API_ROOT}v3/collections/foo/bar/versions/1.0.0/move/staging/rejected/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def deprecate_collections(user, password, expect_pass):
    if foo_namespace_exists():
        if foo_collection_exists('staging'):
            approve_collections(ADMIN_USER, ADMIN_PASSWORD, True)
        if foo_collection_exists('rejected'):
            cleanup_foo_collection()
            approve_collections(ADMIN_USER, ADMIN_PASSWORD, True)
    else:
        approve_collections(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.patch(
        f'{API_ROOT}v3/plugin/ansible/content/published/collections/index/foo/bar/',
        json={"deprecated": True},
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def undeprecate_collections(user, password, expect_pass):
    if foo_namespace_exists():
        if foo_collection_exists('staging'):
            approve_collections(ADMIN_USER, ADMIN_PASSWORD, True)
        if foo_collection_exists('rejected'):
            cleanup_foo_collection()
            approve_collections(ADMIN_USER, ADMIN_PASSWORD, True)
    else:
        approve_collections(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.patch(
        f'{API_ROOT}v3/plugin/ansible/content/published/collections/index/foo/bar/',
        json={"deprecated": False},
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)
