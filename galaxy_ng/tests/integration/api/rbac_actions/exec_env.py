import requests
from datetime import datetime
from time import sleep

from .utils import (
    ADMIN_CREDENTIALS,
    ADMIN_USER,
    ADMIN_PASSWORD,
    API_ROOT,
    PULP_API_ROOT,
    CONTAINER_IMAGE,
    NAMESPACE,
    assert_pass,
    container_registry_remote_exists,
    exec_env_exists,
    get_container_image_data,
    get_push_container_pk,
    podman_login,
    podman_build_and_tag,
    podman_push,
    wait_for_task
)

IMAGE_NAME = CONTAINER_IMAGE[0]


def create_exec_env_remote(user, password, expect_pass, extra):
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote(
            {'username': ADMIN_USER},
            ADMIN_PASSWORD,
            True,
            extra
        )
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
            "upstream_name": IMAGE_NAME,
            "registry": create_response["pk"],
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 201, 403)
    return response.json()


def update_exec_env(user, password, expect_pass, extra):
    print(f'46 container_registry_remote_exists():{container_registry_remote_exists()}')
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote(
            {'username': ADMIN_USER},
            ADMIN_PASSWORD,
            True,
            extra
        )
    print(f'51 exec_env_exists:{exec_env_exists()}')
    if exec_env_exists():
        print(f'53 exec_env_exists:{exec_env_exists()}')
        ee_create_resp = exec_env_exists()
    else:
        ee_create_resp = create_exec_env_remote({'username': ADMIN_USER}, ADMIN_PASSWORD, True)
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
    assert_pass(expect_pass, response.status_code, 201, 403)


def delete_exec_env(user, password, expect_pass, extra):
    if exec_env_exists():
        ee_create_resp = exec_env_exists()
    else:
        ee_create_resp = create_exec_env_remote(
            {'username': ADMIN_USER},
            ADMIN_PASSWORD,
            True,
            extra
        )
    path = "_ui/v1/execution-environments/repositories/"
    response = requests.delete(
        f"{API_ROOT}{path}{ee_create_resp['name']}/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def change_exec_env_desc(user, password, expect_pass, extra):
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote(
            {'username': ADMIN_USER},
            ADMIN_PASSWORD,
            True,
            extra
        )
    if exec_env_exists():
        ee_create_resp = exec_env_exists()
    else:
        ee_create_resp = create_exec_env_remote({'username': ADMIN_USER}, ADMIN_PASSWORD, True)
    response = requests.put(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/{ee_create_resp['pulp_id']}/",
        json={
            "name": ee_create_resp['name'],
            "upstream_name": IMAGE_NAME,
            "registry": create_response["pk"],
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def change_exec_env_desc_object(user, password, expect_pass, extra):
    pass


def change_exec_env_readme(user, password, expect_pass, extra):
    if exec_env_exists():
        ee_create_resp = exec_env_exists()
    else:
        ee_create_resp = create_exec_env_remote(
            {'username': ADMIN_USER},
            ADMIN_PASSWORD,
            True,
            extra
        )
    path = "_ui/v1/execution-environments/repositories/"
    response = requests.put(
        f"{API_ROOT}{path}{ee_create_resp['name']}/_content/readme/",
        json={"text": "Praise the readme!"},
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def change_exec_env_readme_object(user, password, expect_pass, extra):
    pass


def create_execution_environment_local(user, password, expect_pass, extra):
    return_code = podman_login(user['username'], password)
    if return_code == 0:
        return_code = podman_build_and_tag(user['username'], index=0)
    if return_code == 0:
        return_code = podman_push(tag=user['username'], index=0)
    if expect_pass:
        assert return_code == 0
    else:
        assert return_code != 0


def create_containers_under_existing_container_namespace(user, password, expect_pass, extra):
    return_code = podman_login(ADMIN_USER, ADMIN_PASSWORD)
    if return_code == 0:
        return_code = podman_build_and_tag(tag=user['username'], index=0)
    if return_code == 0:
        return_code = podman_push(tag=ADMIN_USER, index=0)

    # push new container to existing namespace
    return_code = podman_login(user['username'], password)
    if return_code == 0:
        return_code = podman_build_and_tag(tag=user['username'], index=1)
    if return_code == 0:
        return_code = podman_push(tag=user['username'], index=1)

    if expect_pass:
        assert return_code == 0
    else:
        assert return_code != 0


def push_containers_to_existing_container_namespace(user, password, expect_pass, extra):
    # create container
    return_code = podman_login(ADMIN_USER, ADMIN_PASSWORD)
    if return_code == 0:
        return_code = podman_build_and_tag(tag=ADMIN_USER, index=0)
    if return_code == 0:
        return_code = podman_push(tag=ADMIN_USER, index=0)

    # repush existing container
    return_code = podman_login(user['username'], password)
    if return_code == 0:
        return_code = podman_build_and_tag(tag=user['username'], index=0)
    if return_code == 0:
        return_code = podman_push(tag=user, index=0)
    if expect_pass:
        assert return_code == 0
    else:
        assert return_code != 0


def change_container_namespace(user, password, expect_pass, extra):
    pass


def change_container_namespace_object(user, password, expect_pass, extra):
    pass


def tag_untag_container_namespace(user, password, expect_pass, extra):
    # create container namespace
    return_code = podman_login(ADMIN_USER, ADMIN_PASSWORD)
    if return_code == 0:
        return_code = podman_build_and_tag(tag=user['username'], index=0)
    if return_code == 0:
        return_code = podman_push(tag=ADMIN_USER, index=0)

    # get image & push container data
    image_data = get_container_image_data()
    push_container_pk = get_push_container_pk()
    # Tag
    response = requests.post(
        f'{PULP_API_ROOT}repositories/container/container-push/{push_container_pk}/tag/',
        json={
            'digest': image_data['digest'],
            'tag': user['username']
        },
        auth=(user['username'], password)
    )
    assert_pass(expect_pass, response.status_code, 202, 403)
    if response.status_code == 202:
        wait_for_task(response)

    # Untag
    response = requests.post(
        f'{PULP_API_ROOT}repositories/container/container-push/{push_container_pk}/untag/',
        json={'tag': user['username']},
        auth=(user['username'], password)
    )
    assert_pass(expect_pass, response.status_code, 202, 403)
    if response.status_code == 202:
        wait_for_task(response)


def sync_remote_container(user, password, expect_pass, extra):
    if not container_registry_remote_exists():
        create_container_registry_remote({'username': ADMIN_USER}, ADMIN_PASSWORD, True, extra)
    if exec_env_exists():
        ee_resp = exec_env_exists()
    else:
        ee_resp = create_exec_env_remote({'username': ADMIN_USER}, ADMIN_PASSWORD, True, extra)
    response = requests.post(
        f'{API_ROOT}_ui/v1/execution-environments/repositories/{ee_resp["name"]}/_content/sync/',
        auth=(user['username'], password)
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def create_container_registry_remote(user, password, expect_pass, extra):
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
    assert_pass(expect_pass, response.status_code, 201, 403)
    return response.json()


def change_container_registry_remote(user, password, expect_pass, extra):
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote({'username': ADMIN_USER}, ADMIN_PASSWORD, True, extra)
        while not container_registry_remote_exists():
            sleep(5)
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
    assert_pass(expect_pass, response.status_code, 200, 403)


def delete_container_registry_remote(user, password, expect_pass, extra):
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote({'username': ADMIN_USER}, ADMIN_PASSWORD, True, extra)
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
    assert_pass(expect_pass, response.status_code, 204, 403)


def create_remote_container(user, password, expect_pass, extra):
    pass


def index_exec_env(user, password, expect_pass, extra):
    if container_registry_remote_exists():
        create_response = container_registry_remote_exists()
    else:
        create_response = create_container_registry_remote({'username': ADMIN_USER}, ADMIN_PASSWORD, True, extra)
    response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{create_response['pk']}/index/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 400, 403)
