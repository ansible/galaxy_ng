import requests
from datetime import datetime

from .utils import (
    ADMIN_CREDENTIALS,
    API_ROOT,
    NAMESPACE,
    gen_string,
)


def create_exec_env(user, password, expect_pass):
    create_response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/",
        json={
            "name": f"{NAMESPACE}_remote_registry_{gen_string()}",
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
        auth=ADMIN_CREDENTIALS,
    )
    response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/",
        json={
            "name": f"{NAMESPACE}_exec_env_{gen_string()}",
            "upstream_name": "ubi8-minimal",
            "registry": create_response.json()["pk"],
        },
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 201
    else:
        assert response.status_code == 403


def delete_exec_env(user, password, expect_pass):
    create_response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/",
        json={
            "name": f"{NAMESPACE}_remote_registry_{gen_string()}",
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
        auth=ADMIN_CREDENTIALS,
    )
    ee_create_resp = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/",
        json={
            "name": f"{NAMESPACE}_exec_env_{gen_string()}",
            "upstream_name": "ubi8-minimal",
            "registry": create_response.json()["pk"],
        },
        auth=ADMIN_CREDENTIALS,
    )
    path = "_ui/v1/execution-environments/repositories/"
    response = requests.delete(
        f"{API_ROOT}{path}{ee_create_resp.json()['name']}/",
        json={
            "name": f"{NAMESPACE}_exec_env_{gen_string()}",
            "upstream_name": "ubi8-minimal",
            "registry": create_response.json()["pk"],
        },
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 202
    else:
        assert response.status_code == 403


def change_exec_env_desc(user, password, expect_pass):
    create_response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/",
        json={
            "name": f"{NAMESPACE}_remote_registry_{gen_string()}",
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
        auth=ADMIN_CREDENTIALS,
    )
    ex_env_create_resp = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/",
        json={
            "name": f"{NAMESPACE}_exec_env_{gen_string()}",
            "upstream_name": "ubi8-minimal",
            "registry": create_response.json()["pk"],
        },
        auth=ADMIN_CREDENTIALS,
    )
    response = requests.put(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/{ex_env_create_resp.json()['pulp_id']}/",
        json={
            "name": ex_env_create_resp.json()['name'],
            "upstream_name": "ubi8-minimal",
            "registry": create_response.json()["pk"],
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
    create_response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/",
        json={
            "name": f"{NAMESPACE}_remote_registry_{gen_string()}",
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
        auth=ADMIN_CREDENTIALS,
    )
    ee_create_resp = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/",
        json={
            "name": f"{NAMESPACE}_exec_env_{gen_string()}",
            "upstream_name": "ubi8-minimal",
            "registry": create_response.json()["pk"],
        },
        auth=ADMIN_CREDENTIALS,
    )
    path = "_ui/v1/execution-environments/repositories/"
    response = requests.put(
        f"{API_ROOT}{path}{ee_create_resp.json()['name']}/_content/readme/",
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
    response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/",
        json={
            "name": f"{NAMESPACE}_remote_registry_{gen_string()}",
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


def change_container_registry_remote(user, password, expect_pass):
    # Create container registry remote to change
    create_response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/",
        json={
            "name": f"{NAMESPACE}_remote_registry_{gen_string()}",
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
        auth=ADMIN_CREDENTIALS,
    )
    response = requests.put(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{create_response.json()['pk']}/",
        json={
            "name": create_response.json()['name'],
            "url": create_response.json()['url'],
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
    # Create container registry remote to delete
    create_response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/",
        json={
            "name": f"{NAMESPACE}_remote_registry_{gen_string()}",
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
        auth=ADMIN_CREDENTIALS,
    )
    response = requests.delete(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{create_response.json()['pk']}/",
        json={
            "name": create_response.json()['name'],
            "url": create_response.json()['url'],
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
    create_response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/",
        json={
            "name": f"{NAMESPACE}_remote_registry_{gen_string()}",
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
        auth=ADMIN_CREDENTIALS,
    )
    response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{create_response.json()['pk']}/index/",
        auth=(user['username'], password),
    )
    if expect_pass:
        # action allowed, unsupported on remote registry
        assert response.status_code == 400
    else:
        assert response.status_code == 403
