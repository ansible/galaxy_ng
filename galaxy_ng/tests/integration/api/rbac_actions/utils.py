import os
import random
from galaxy_ng.tests.integration.api.test_collection_signing import namespace
from galaxy_ng.tests.integration.conftest import ansible_config, artifact
import requests
import string
import time
from subprocess import Popen, PIPE, STDOUT
from urllib.parse import urljoin
from galaxy_ng.tests.integration.utils import (
    build_collection,
    upload_artifact,
    get_client,
    wait_for_task as wait_for_task_fixtures,
    TaskWaitingTimeout
)
from galaxy_ng.tests.integration.conftest import AnsibleConfigFixture

from ansible.galaxy.api import GalaxyError

CLIENT_CONFIG = AnsibleConfigFixture("ansible_partner")

API_ROOT = CLIENT_CONFIG["url"]
PULP_API_ROOT = f"{API_ROOT}pulp/api/v3/"
SERVER = API_ROOT.split("/api/")[0]

ADMIN_USER = CLIENT_CONFIG["username"]
ADMIN_PASSWORD = CLIENT_CONFIG["password"]

ADMIN_CREDENTIALS = (ADMIN_USER, ADMIN_PASSWORD)

NAMESPACE = "rbac_roles_test"
PASSWORD = "p@ssword!"
TLS_VERIFY = "--tls-verify=false"
IMAGE_NAME = "ubi9-minimal"

REQUIREMENTS_FILE = "collections:\n  - name: newswangerd.collection_demo\n"  # noqa: 501


class InvalidResponse(Exception):
    pass


def assert_pass(expect_pass, code, pass_status, deny_status):
    if code not in (pass_status, deny_status):
        raise InvalidResponse(f'Invalid response status code: {code}')

    if expect_pass:
        assert code == pass_status
    else:
        assert code == deny_status


def gen_string(size=10, chars=string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))


def create_group_with_user_and_role(user, role, content_object=None, group=None):
    if not group:
        group = f"{NAMESPACE}_group_{gen_string()}"
    else:
        if group_exists(group):
            group_id = group_exists(group)['id']
            requests.delete(
                f"{API_ROOT}_ui/v1/groups/{group_id}/",
                auth=ADMIN_CREDENTIALS,
            )
    response = requests.post(
        API_ROOT + "_ui/v1/groups/",
        json={"name": group},
        auth=ADMIN_CREDENTIALS
    )
    group_id = response.json()["id"]
    requests.post(
        f"{API_ROOT}_ui/v1/groups/{group_id}/users/",
        json={"username": user["username"]},
        auth=ADMIN_CREDENTIALS
    )
    requests.post(
        f"{PULP_API_ROOT}groups/{group_id}/roles/",
        json={"role": role, "content_object": content_object},
        auth=ADMIN_CREDENTIALS
    )
    return response.json()


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


def wait_for_task(resp, path=None, timeout=300):
    ready = False
    host = SERVER
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


def group_exists(group_name='rbac_roles_test_group'):
    response = requests.get(
        f'{API_ROOT}_ui/v1/groups?name={group_name}',
        auth=ADMIN_CREDENTIALS
    )
    if response.json()['meta']['count'] == 1:
        return response.json()['data'][0]
    else:
        return False


def collection_namespace_exists(ns_name='rbac_roles_test_col_ns'):
    response = requests.get(
        f'{API_ROOT}_ui/v1/namespaces?name={ns_name}',
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


def object_user_exists(username):
    response = requests.get(
        f"{API_ROOT}_ui/v1/users/?username={NAMESPACE}_user_ns_object",
        auth=ADMIN_CREDENTIALS
    ).json()
    if response['meta']['count'] == 1:
        return response['data'][0]
    else:
        return False


def podman_login(user, password):
    cmd = [
        "podman",
        "login",
        "--username",
        f"{user['username']}",
        "--password",
        f"{password}",
        "localhost:5001",
        TLS_VERIFY
    ]
    proc = Popen(cmd, stdout=PIPE, stderr=STDOUT, encoding="utf-8")
    return proc.wait()


def podman_build_and_tag(tag):
    cmd = [
        "podman",
        "image",
        "build",
        "-t",
        f"localhost:5001/{IMAGE_NAME}:{tag}",
        f"{os.path.dirname(__file__)}/",
        TLS_VERIFY
    ]
    proc = Popen(cmd, stdout=PIPE, stderr=STDOUT, encoding="utf-8")
    return proc.wait()


def podman_push(user):
    cmd = [
        "podman",
        "image",
        "push",
        f"localhost:5001/{IMAGE_NAME}:{user['username']}",
        "--remove-signatures",
        TLS_VERIFY
    ]
    proc = Popen(cmd, stdout=PIPE, stderr=STDOUT, encoding="utf-8")
    return proc.wait()


def del_user(pk):
    requests.delete(
        f"{API_ROOT}_ui/v1/users/{pk}/",
        auth=(ADMIN_CREDENTIALS),
    )


def create_group(name):
    return requests.post(
        f"{API_ROOT}_ui/v1/groups/",
        json={"name": name},
        auth=ADMIN_CREDENTIALS
    ).json()


def del_group(pk):
    return requests.delete(
        f"{API_ROOT}_ui/v1/groups/{pk}/",
        auth=ADMIN_CREDENTIALS
    )


def create_role(name):
    return requests.post(
        f"{PULP_API_ROOT}roles/",
        json={
            "name": name,
            "permissions": [],
        },
        auth=ADMIN_CREDENTIALS,
    ).json()


def del_role(href):
    requests.delete(
        f"{SERVER}{href}",
        auth=ADMIN_CREDENTIALS
    )


def del_namespace(name):
    return requests.delete(
        f"{API_ROOT}_ui/v1/namespaces/{name}/",
        auth=ADMIN_CREDENTIALS,
    )


def del_collection(name, namespace, repo="staging"):
    requests.delete(
        f"{API_ROOT}v3/plugin/ansible/content/{repo}/collections/index/{namespace}/{name}/",
        auth=ADMIN_CREDENTIALS,
    )


def gen_namespace(name, groups=None):
    groups = groups or []

    return requests.post(
        f"{API_ROOT}_ui/v1/namespaces/",
        json={
            "name": name,
            "groups": groups,
        },
        auth=ADMIN_CREDENTIALS,
    ).json()


def gen_collection(name, namespace):
    artifact = build_collection(
        name=name,
        namespace=namespace
    )

    ansible_config = AnsibleConfigFixture("ansible_partner", namespace=artifact.namespace)

    client = get_client(ansible_config)

    wait_for_task_fixtures(client, upload_artifact(ansible_config, client, artifact))

    resp = requests.get(
        f"{PULP_API_ROOT}content/ansible/collection_versions/?name={name}&namespace={namespace}",
        auth=ADMIN_CREDENTIALS
    )

    return resp.json()["results"][0]


def reset_remote():
    return requests.put(
        f"{API_ROOT}content/community/v3/sync/config/",
        json={
            "url": "https://example.com/",
            "auth_url": None,
            "token": None,
            "policy": "immediate",
            "requirements_file": REQUIREMENTS_FILE,
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
    ).json()


def gen_ee_namespace(name):
    pass


def wait_for_all_tasks(timeout=300):
    ready = False
    wait_until = time.time() + timeout

    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        running_count = requests.get(
            PULP_API_ROOT + "tasks/?state=running",
            auth=ADMIN_CREDENTIALS
        ).json()["count"]

        waiting_count = requests.get(
            PULP_API_ROOT + "tasks/?state=waiting",
            auth=ADMIN_CREDENTIALS
        ).json()["count"]

        ready = running_count == 0 and waiting_count == 0

        time.sleep(1)


class ReusableCollection:
    """
    This provides a reusable namespace and collection so that a new collection
    doesn't have to be created for every test that needs to modify one.
    """

    def __init__(self, name, groups=None):
        self._namespace_name = f"c_ns_{name}"
        self._collection_name = f"col_{name}"

        self._namespace = gen_namespace(self._namespace_name, groups)

        self._published_href = self._get_repo_href("published")
        self._rejected_href = self._get_repo_href("rejected")
        self._staging_href = self._get_repo_href("staging")

    def _add_to_repo(self, repo_href, content_href):
        requests.post(
            f"{SERVER}{repo_href}modify/",
            json={
                "add_content_units": [content_href,],
            },
            auth=ADMIN_CREDENTIALS,
        )

    def _remove_from_repo(self, repo_href, content_href):
        requests.post(
            f"{SERVER}{repo_href}modify/",
            json={
                "remove_content_units": [content_href,],
            },
            auth=ADMIN_CREDENTIALS,
        )

    def _get_repo_href(self, name):
        return requests.get(
            f"{PULP_API_ROOT}repositories/ansible/ansible/?name={name}",
            auth=ADMIN_CREDENTIALS
        ).json()["results"][0]["pulp_href"]
    

    def _reset_collection(self):
        resp = requests.get(
            (
                f"{PULP_API_ROOT}content/ansible/collection_versions/"
                f"?name={self._collection_name}&namespace="
                f"{self._namespace_name}"),
            auth=ADMIN_CREDENTIALS
        )

        # Make sure the collection exists
        if resp.json()["count"] == 0:
            self._collection = gen_collection(
                self._collection_name, self._namespace_name)
            self._collection_href = self._collection["pulp_href"]
        else:

            # If it doesn't, reset it's state.
            self._remove_from_repo(self._rejected_href, self._collection_href)
            self._remove_from_repo(self._published_href, self._collection_href)
            self._add_to_repo(self._staging_href, self._collection_href)

        wait_for_all_tasks()

        requests.patch(
            f'{API_ROOT}v3/plugin/ansible/content/staging/collections/index/{self._namespace_name}/{self._collection_name}/',
            json={"deprecated": False},
            auth=ADMIN_CREDENTIALS,
        )

    def get_namespace(self):
        return self._namespace

    def get_collection(self):
        self._reset_collection()
        return self._collection

    def cleanup(self):
        collection = self.get_collection()
        namespace = self.get_namespace()

        del_collection(collection['name'], collection['namespace'])
        wait_for_all_tasks()
        del_namespace(namespace['name'])


class ReusableEE:
    def __init__(self, name):
        self.namespace_name = f"ns_{gen_string()}"
        self.ee_name = f"ee_{gen_string()}"
    
    