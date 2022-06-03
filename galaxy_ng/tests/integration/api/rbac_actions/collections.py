import datetime
import requests

from .utils import (
    ADMIN_CREDENTIALS,
    API_ROOT,
    NAMESPACE,
    gen_string,
    wait_for_task,
)

requirements_file = "collections:\n  - name: newswangerd.collection_demo\n    version: 1.0.11\n    source: https://galaxy.ansible.com"


def create_collection_namespace(user, password, expect_pass):
    print(f'user:{user}')
    print(f'expect_pass:{expect_pass}')
    response = requests.post(
        f"{API_ROOT}_ui/v1/namespaces/",
        json={
            "name": f"{NAMESPACE}_namespace_{gen_string()}",
            "groups": [{
                "name": "system:partner-engineers",
                "object_roles": ["galaxy.content_admin"]
            }],
        },
        auth=('rbac_roles_user_izibxxpzey', 'p@ssword!'),
    )
    print(f'response.status_code:{response.status_code}')
    if expect_pass:
        assert response.status_code == 201
    else:
        assert response.status_code == 403


def change_collection_namespace(user, password, expect_pass, namespace=None):
    # Create namespace to change
    if namespace is None:
        response = requests.post(
            f"{API_ROOT}_ui/v1/namespaces/",
            json={
                "name": f"{NAMESPACE}_namespace_{gen_string()}",
                "groups": [{
                    "name": "system:partner-engineers",
                    "object_roles": ["galaxy.content_admin"]
                }],
            },
            auth=ADMIN_CREDENTIALS,
        )
    namespace_name = response.json()["name"]
    namespace_groups = response.json()["groups"]
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
    response = requests.post(
        f"{API_ROOT}_ui/v1/namespaces/",
        json={
            "name": f"{NAMESPACE}_namespace_{gen_string()}",
            "groups": [{
                "name": "system:partner-engineers",
                "object_roles": ["galaxy.content_admin"]
            }],
        },
        auth=(user['username'], password),
    )
    if response.status_code != 403:
        namespace_name = response.json()["name"]
        response = requests.delete(
            f"{API_ROOT}_ui/v1/namespaces/{namespace_name}/",
            auth=(user['username'], password),
        )
    if expect_pass:
        assert response.status_code == 204
    else:
        assert response.status_code == 403


def upload_collection_to_namespace(user, password, expect_pass):
    # Make and build a collection to upload
    # ansible-galaxy collection init foo.bar
    # cd foo/bar
    # mkdir meta
    # cd meta
    # printf "requires_ansible: '>=2.9.10,<2.11.5'" > runtime.yml
    # cd ..
    # ansible-galaxy collection build
    # cd $TMPDIR

    # Upload collection
    # ansible-galaxy collection publish foo-bar-*.tar.gz
    pass


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


def approve_reject_collections(user, password, expect_pass):
    # upload collection
    # approve collection
    pass


def deprecate_collections(user, password, expect_pass):
    # Configure and sync a community collection
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
        auth=ADMIN_CREDENTIALS,
    )
    # Sync community collection
    response = requests.post(
        f"{API_ROOT}content/community/v3/sync/",
        auth=ADMIN_CREDENTIALS,
    )
    wait_for_task(response)
    # Deprecate community collection
    col = "collection_demo"
    ns = "newswangerd"
    response = requests.patch(
        f'{API_ROOT}v3/plugin/ansible/content/community/collections/index/{ns}/{col}/',
        auth=ADMIN_CREDENTIALS,
    )
    if expect_pass:
        assert response.status_code == 202
    else:
        assert response.status_code == 403


def undeprecate_collections(user, password, expect_pass):
    # Same as deprecating a collection?
    deprecate_collections(user, password, expect_pass)
