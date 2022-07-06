import requests
from datetime import datetime

from .utils import (
    ADMIN_CREDENTIALS,
    ADMIN_USER,
    ADMIN_PASSWORD,
    API_ROOT,
    NAMESPACE,
    container_registry_remote_exists,
    exec_env_exists,
)


def create_exec_env(user, password, expect_pass):
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote(ADMIN_USER, ADMIN_PASSWORD, True)
    if exec_env_exists():
        ee_create_resp = exec_env_exists()
        path = "_ui/v1/execution-environments/repositories/"
        response = requests.delete(
            f"{API_ROOT}{path}{ee_create_resp['name']}/",
            auth=ADMIN_CREDENTIALS,
        )
    response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/",
        json={
            "name": f"{NAMESPACE}_exec_env",
            "upstream_name": "ubi8-minimal",
            "registry": create_response["pk"],
        },
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 201
    else:
        assert response.status_code == 403
    return response.json()


def update_exec_env(user, password, expect_pass):
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote(ADMIN_USER, ADMIN_PASSWORD, True)
    if exec_env_exists():
        ee_create_resp = exec_env_exists()
    else:
        ee_create_resp = create_exec_env(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.put(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/{ee_create_resp['pulp_id']}/",
        json={
            "name": ee_create_resp['name'],
            "upstream_name": ee_create_resp["upstream_name"],
            "registry": create_response["pk"],
            "include_tags": ["latest"]  # changed
        },
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 201
    else:
        assert response.status_code == 403


def delete_exec_env(user, password, expect_pass):
    if exec_env_exists():
        ee_create_resp = exec_env_exists()
    else:
        ee_create_resp = create_exec_env(ADMIN_USER, ADMIN_PASSWORD, True)
    path = "_ui/v1/execution-environments/repositories/"
    response = requests.delete(
        f"{API_ROOT}{path}{ee_create_resp['name']}/",
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 202
    else:
        assert response.status_code == 403


def change_exec_env_desc(user, password, expect_pass):
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote(ADMIN_USER, ADMIN_PASSWORD, True)
    if exec_env_exists():
        ee_create_resp = exec_env_exists()
    else:
        ee_create_resp = create_exec_env(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.put(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/{ee_create_resp['pulp_id']}/",
        json={
            "name": ee_create_resp['name'],
            "upstream_name": "ubi8-minimal",
            "registry": create_response["pk"],
        },
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def change_exec_env_desc_object(user, password, expect_pass):
    pass


def change_exec_env_readme(user, password, expect_pass):
    if exec_env_exists():
        ee_create_resp = exec_env_exists()
    else:
        ee_create_resp = create_exec_env(ADMIN_USER, ADMIN_PASSWORD, True)
    path = "_ui/v1/execution-environments/repositories/"
    response = requests.put(
        f"{API_ROOT}{path}{ee_create_resp['name']}/_content/readme/",
        json={"text": "Praise the readme!"},
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def change_exec_env_readme_object(user, password, expect_pass):
    pass


def create_containers_under_existing_container_namespace(user, password, expect_pass):
    pass


def push_containers_to_existing_container_namespace(user, password, expect_pass):
    pass


def change_container_namespace(user, password, expect_pass):
    pass


def change_container_namespace_object(user, password, expect_pass):
    pass


def tag_untag_container_namespace(user, password, expect_pass):
    pass


def sync_remote_container(user, password, expect_pass):
    pass


def create_container_registry_remote(user, password, expect_pass):
    if container_registry_remote_exists():
        response = container_registry_remote_exists()
        requests.delete(
            f'{API_ROOT}_ui/v1/execution-environments/registries/{response["pk"]}/',
            auth=ADMIN_CREDENTIALS
        )
    response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/",
        json={
            "name": f"{NAMESPACE}_remote_registry",
            "url": "http://example.com",
            "policy": "immediate",
            "created_at": str(datetime.now()),
            "updated_at": str(datetime.now()),
            "username": None,
            "password": None,
            "tls_validation": False,
            "client_key": None,
            "client_cert": None,
            "ca_cert": None,
            "download_concurrency": None,
            "proxy_url": None,
            "proxy_username": None,
            "proxy_password": None,
            "rate_limit": None,
        },
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 201
    else:
        assert response.status_code == 403
    return response.json()


def change_container_registry_remote(user, password, expect_pass):
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.put(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{create_response['pk']}/",
        json={
            "name": create_response['name'],
            "url": create_response['url'],
            "policy": "immediate",
            "created_at": str(datetime.now()),
            "updated_at": str(datetime.now()),
            "username": None,
            "password": None,
            "tls_validation": False,
            "client_key": None,
            "client_cert": None,
            "ca_cert": None,
            "download_concurrency": 10,  # changed
            "proxy_url": None,
            "proxy_username": None,
            "proxy_password": None,
            "rate_limit": 8,  # changed
        },
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def delete_container_registry_remote(user, password, expect_pass):
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.delete(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{create_response['pk']}/",
        json={
            "name": create_response['name'],
            "url": create_response['url'],
            "policy": "immediate",
            "created_at": str(datetime.now()),
            "updated_at": str(datetime.now()),
            "username": None,
            "password": None,
            "tls_validation": False,
            "client_key": None,
            "client_cert": None,
            "ca_cert": None,
            "download_concurrency": 10,
            "proxy_url": None,
            "proxy_username": None,
            "proxy_password": None,
            "rate_limit": 8,
        },
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 204
    else:
        assert response.status_code == 403


def create_remote_container(user, password, expect_pass):
    pass


def index_exec_env(user, password, expect_pass):
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote(ADMIN_USER, ADMIN_PASSWORD, True)
    response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{create_response['pk']}/index/",
        auth=(user['username'], password),
    )
    if expect_pass:
        # action allowed, unsupported on remote registry
        assert response.status_code == 400
    else:
        assert response.status_code == 403
