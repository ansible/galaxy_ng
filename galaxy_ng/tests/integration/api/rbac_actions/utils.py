import random
import requests
import string
import time
from urllib.parse import urljoin

from ansible.galaxy.api import GalaxyError

NAMESPACE = "rbac_roles_test"
PASSWORD = "p@ssword!"
ADMIN_CREDENTIALS = ("admin", "admin")
API_ROOT = "http://localhost:5001/api/automation-hub/"
PULP_API_ROOT = "http://localhost:5001/api/automation-hub/pulp/api/v3/"
ADMIN_USER = {'username': 'admin'}
ADMIN_PASSWORD = "admin"


class TaskWaitingTimeout(Exception):
    pass


def gen_string(size=10, chars=string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))


def create_group_with_user_and_role(user, role):
    response = requests.post(
        API_ROOT + "_ui/v1/groups/",
        json={"name": f"{NAMESPACE}_group_{gen_string()}"},
        auth=ADMIN_CREDENTIALS
    )
    group_id = response.json()["id"]
    response = requests.post(
        f"{API_ROOT}_ui/v1/groups/{group_id}/users/",
        json={"username": user["username"]},
        auth=ADMIN_CREDENTIALS
    )
    response = requests.post(
        f"{PULP_API_ROOT}groups/{group_id}/roles/",
        json={"role": role, "content_object": None},
        auth=ADMIN_CREDENTIALS
    )
    return group_id


def create_user(username, password):
    response = requests.post(
        f"{API_ROOT}_ui/v1/users/",
        json={
            "username": username,
            "first_name": "",
            "last_name": "",
            "email": "",
            "group": "",
            "password": password,
            "description": "",
        },
        auth=ADMIN_CREDENTIALS,
    )
    return response.json()


def cleanup_foo_collection():
    # cleanup collection
    foo_staging_exists = requests.get(
        f"{API_ROOT}v3/plugin/ansible/content/staging/collections/index/foo/bar/",
        auth=ADMIN_CREDENTIALS
    ).status_code == 200
    if foo_staging_exists:
        response = requests.delete(
            f"{API_ROOT}v3/plugin/ansible/content/staging/collections/index/foo/bar/",
            auth=ADMIN_CREDENTIALS,
        )
        if response.status_code != 404:
            wait_for_task(response)
    foo_published_exists = requests.get(
        f"{API_ROOT}v3/plugin/ansible/content/published/collections/index/foo/bar/",
        auth=ADMIN_CREDENTIALS
    ).status_code == 200
    if foo_published_exists:
        response = requests.delete(
            f"{API_ROOT}v3/plugin/ansible/content/published/collections/index/foo/bar/",
            auth=ADMIN_CREDENTIALS,
        )
        if response.status_code != 404:
            wait_for_task(response)
    foo_rejected_exists = requests.get(
        f"{API_ROOT}v3/plugin/ansible/content/rejected/collections/index/foo/bar/",
        auth=ADMIN_CREDENTIALS
    ).status_code == 200
    if foo_rejected_exists:
        response = requests.delete(
            f"{API_ROOT}v3/plugin/ansible/content/rejected/collections/index/foo/bar/",
            auth=ADMIN_CREDENTIALS,
        )
        if response.status_code != 404:
            wait_for_task(response)
    # cleanup namespace
    response = requests.delete(
        f"{API_ROOT}_ui/v1/namespaces/foo/",
        auth=ADMIN_CREDENTIALS,
    )


def wait_for_task(resp, path=None, timeout=300):
    ready = False
    host = 'http://localhost:5001'
    # Community collection delete wasn't providing path with task pk
    if path is not None:
        url = urljoin(f"{PULP_API_ROOT}{path}", f'{resp.json()["task"]}/')
    else:
        url = urljoin(f"{host}", f"{resp.json()['task']}")
    wait_until = time.time() + timeout
    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        try:
            resp = requests.get(url, auth=ADMIN_CREDENTIALS)
        except GalaxyError as e:
            if "500" not in str(e):
                raise
        else:
            ready = resp.json()["state"] not in ("running", "waiting")
        time.sleep(5)
    return resp


def foo_collection_exists(repo):
    return requests.get(
        f'{API_ROOT}v3/plugin/ansible/content/{repo}/collections/index/foo/bar/',
        auth=ADMIN_CREDENTIALS
    ).status_code == 200


def foo_namespace_exists():
    return requests.get(
        f"{API_ROOT}_ui/v1/namespaces/foo/",
        auth=ADMIN_CREDENTIALS
    ).status_code == 200


def user_exists():
    response = requests.get(
        f'{API_ROOT}_ui/v1/users?username=rbac_roles_test_user',
        auth=ADMIN_CREDENTIALS
    )
    if response.json()['meta']['count'] == 1:
        return response.json()['data'][0]
    else:
        return False


def role_exists():
    response = requests.get(
        f'{PULP_API_ROOT}roles?name=rbac_roles_test_role',
        auth=ADMIN_CREDENTIALS
    )
    if response.json()['count'] == 1:
        return response.json()['results'][0]
    else:
        return False


def group_exists():
    response = requests.get(
        f'{API_ROOT}_ui/v1/groups?name=rbac_roles_test_group',
        auth=ADMIN_CREDENTIALS
    )
    if response.json()['meta']['count'] == 1:
        return response.json()['data'][0]
    else:
        return False


def collection_namespace_exists():
    response = requests.get(
        f'{API_ROOT}_ui/v1/namespaces?name=rbac_roles_test_col_ns',
        auth=ADMIN_CREDENTIALS
    )
    if response.json()['meta']['count'] == 1:
        return response.json()['data'][0]
    else:
        return False


def container_registry_remote_exists():
    response = requests.get(
        f'{API_ROOT}_ui/v1/execution-environments/registries/?name={NAMESPACE}_remote_registry',
        auth=ADMIN_CREDENTIALS
    )
    if response.json()['meta']['count'] == 1:
        return response.json()['data'][0]
    else:
        return False


def exec_env_exists():
    response = requests.get(
        f'{API_ROOT}_ui/v1/execution-environments/remotes/',
        auth=ADMIN_CREDENTIALS
    )
    remote = next(
        (item for item in response.json()['data'] if item["name"] == f"{NAMESPACE}_exec_env"),
        False
    )
    return remote
