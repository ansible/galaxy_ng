import os
import requests
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT

from .utils import (
    ADMIN_CREDENTIALS,
    ADMIN_PASSWORD,
    ADMIN_USER,
    API_ROOT,
    NAMESPACE,
    cleanup_foo_collection,
    gen_string,
)

requirements_file = "collections:\n  - name: newswangerd.collection_demo\n    version: 1.0.11\n    source: https://galaxy.ansible.com"  # noqa: 501


def create_collection_namespace(user, password, expect_pass, cleanup=True):
    response = requests.post(
        f"{API_ROOT}_ui/v1/namespaces/",
        json={
            "name": f"{NAMESPACE}_namespace_{gen_string()}",
            "groups": [],
        },
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 201
    else:
        assert response.status_code == 403
    if expect_pass and cleanup:
        requests.delete(
            f"{API_ROOT}_ui/v1/namespaces/{response.json()['name']}/",
            auth=ADMIN_CREDENTIALS,
        )
    else:
        return response


def change_collection_namespace(user, password, expect_pass, namespace_response=None):
    # Create namespace to change
    if namespace_response is None:
        namespace_response = create_collection_namespace(
            ADMIN_USER,
            ADMIN_PASSWORD,
            True,
            cleanup=False
        )
    namespace_name = namespace_response.json()["name"]
    namespace_groups = namespace_response.json()["groups"]
    response = requests.put(
        f"{API_ROOT}_ui/v1/namespaces/{namespace_name}/",
        json={
            "name": namespace_name,
            "groups": namespace_groups,
            "description": "Praise the description!",
        },
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def delete_collection_namespace(user, password, expect_pass):
    # Create namespace to delete
    create_response = create_collection_namespace(
        ADMIN_USER,
        ADMIN_PASSWORD,
        True,
        cleanup=False
    )
    if create_response.status_code != 403:
        namespace_name = create_response.json()["name"]
        response = requests.delete(
            f"{API_ROOT}_ui/v1/namespaces/{namespace_name}/",
            auth=(user['username'], password),
        )
    if expect_pass:
        assert response.status_code == 204
    else:
        assert response.status_code == 403


def upload_collection_to_namespace(user, password, expect_pass, cleanup=True):
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
        auth=(user['username'], password),
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
            cleanup_foo_collection()
    if cleanup:
        cleanup_foo_collection()


def delete_collection(user, password, expect_pass):
    cleanup_foo_collection()
    upload_collection_to_namespace(ADMIN_USER, ADMIN_PASSWORD, True, cleanup=False)
    response = requests.delete(
        f"{API_ROOT}v3/plugin/ansible/content/staging/collections/index/foo/bar/",
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 202
    else:
        assert response.status_code == 403
    cleanup_foo_collection()


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
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def launch_collection_sync(user, password, expect_pass):
    configure_collection_sync(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.post(
        f"{API_ROOT}content/community/v3/sync/",
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def view_sync_configuration(user, password, expect_pass):
    response = requests.get(
        f"{API_ROOT}content/community/v3/sync/config/",
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def approve_collections(user, password, expect_pass, cleanup=True):
    cleanup_foo_collection()
    upload_collection_to_namespace(ADMIN_USER, ADMIN_PASSWORD, True, cleanup=False)
    response = requests.post(
        f"{API_ROOT}v3/collections/foo/bar/versions/1.0.0/move/staging/published/",
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 202
    else:
        assert response.status_code == 403
    if cleanup:
        cleanup_foo_collection()


def reject_collections(user, password, expect_pass):
    cleanup_foo_collection()
    upload_collection_to_namespace(ADMIN_USER, ADMIN_PASSWORD, True, cleanup=False)
    response = requests.post(
        f"{API_ROOT}v3/collections/foo/bar/versions/1.0.0/move/staging/rejected/",
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 202
    else:
        assert response.status_code == 403
    cleanup_foo_collection()


def deprecate_collections(user, password, expect_pass):
    # Upload and approve collection
    approve_collections(user, password, True, cleanup=False)
    response = requests.patch(
        f'{API_ROOT}v3/plugin/ansible/content/published/collections/index/foo/bar/',
        json={"deprecated": True},
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 202
    else:
        assert response.status_code == 403
    cleanup_foo_collection()


def undeprecate_collections(user, password, expect_pass):
    # Upload and approve collection
    approve_collections(user, password, True, cleanup=False)
    response = requests.patch(
        f'{API_ROOT}v3/plugin/ansible/content/published/collections/index/foo/bar/',
        json={"deprecated": False},
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 202
    else:
        assert response.status_code == 403
    cleanup_foo_collection()
