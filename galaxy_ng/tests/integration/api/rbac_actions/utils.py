import random
import requests
import string
import time
import subprocess
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

CLIENT_CONFIG = AnsibleConfigFixture("admin")

API_ROOT = CLIENT_CONFIG["url"]
PULP_API_ROOT = f"{API_ROOT}pulp/api/v3/"
SERVER = API_ROOT.split("/api/")[0]

ADMIN_USER = CLIENT_CONFIG["username"]
ADMIN_PASSWORD = CLIENT_CONFIG["password"]
ADMIN_TOKEN = CLIENT_CONFIG["token"]

ADMIN_CREDENTIALS = (ADMIN_USER, ADMIN_PASSWORD)

NAMESPACE = "rbac_roles_test"
PASSWORD = "p@ssword!"
TLS_VERIFY = "--tls-verify=false"
CONTAINER_IMAGE = ["foo/ubi9-minimal", "foo/ubi8-minimal"]

REQUIREMENTS_FILE = "collections:\n  - name: newswangerd.collection_demo\n"  # noqa: 501

TEST_CONTAINER = "alpine"


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
    name = f"{NAMESPACE}_group_{gen_string()}"

    g = create_group(name)

    requests.post(
        f"{API_ROOT}_ui/v1/groups/{g['id']}/users/",
        json={"username": user["username"]},
        auth=ADMIN_CREDENTIALS
    )
    requests.post(
        f"{PULP_API_ROOT}groups/{g['id']}/roles/",
        json={"role": role, "content_object": content_object},
        auth=ADMIN_CREDENTIALS
    )
    return g


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


def ensure_test_container_is_pulled():
    cmd = ["podman", "container", "exists", TEST_CONTAINER]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 1:
        cmd = ["podman", "image", "pull", "alpine"]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def podman_push(username, password, container, tag="latest"):
    ensure_test_container_is_pulled()

    new_container = f"localhost:5001/{container}:{tag}"

    tag_cmd = ["podman", "image", "tag", TEST_CONTAINER, new_container]
    subprocess.run(tag_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    push_cmd = [
        "podman",
        "push",
        "--creds",
        f"{username}:{password}",
        new_container,
        "--remove-signatures",
        "--tls-verify=false"]

    return subprocess.run(push_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode


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

    ansible_config = AnsibleConfigFixture("admin", namespace=artifact.namespace)

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

    def _reset_collection_repo(self):
        requests.post(
            (
                f"{API_ROOT}v3/collections/{self._namespace_name}"
                f"/{self._collection_name}/versions/{self._collection['version']}"
                "/move/rejected/staging/"
            ),
            auth=ADMIN_CREDENTIALS,
        )
        requests.post(
            (
                f"{API_ROOT}v3/collections/{self._namespace_name}"
                f"/{self._collection_name}/versions/{self._collection['version']}"
                "/move/published/staging/"
            ),
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
            self._reset_collection_repo()

        wait_for_all_tasks()

        url = (
            f'{API_ROOT}v3/plugin/ansible/content/staging/collections/index/'
            f'{self._namespace_name}/{self._collection_name}/'
        )

        requests.patch(
            url,
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


def cleanup_test_obj(response, pk, del_func):
    data = response.json()

    if pk in data:
        del_func(pk)


def del_container(name):
    requests.delete(
        f"{API_ROOT}_ui/v1/execution-environments/repositories/{name}/",
        auth=ADMIN_CREDENTIALS,
    )


def gen_remote_container(name, registry_pk):
    return requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/",
        json={
            "name": name,
            "upstream_name": "foo",
            "registry": registry_pk,
        },
        auth=ADMIN_CREDENTIALS,
    ).json()


def del_registry(pk):
    requests.delete(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{pk}/",
        auth=ADMIN_CREDENTIALS,
    )


def gen_registry(name):
    return requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/",
        json={
            "name": name,
            "url": "http://example.com",
        },
        auth=ADMIN_CREDENTIALS,
    ).json()


class ReusableContainerRegistry:
    def __init__(self, name):
        self._name = f"ee_ns_{name}"
        self._registry = gen_registry(self._name)

    # def _reset(self):
    #     data = requests.get(
    #         f'{API_ROOT}_ui/v1/execution-environments/registries/?name={self._name}',
    #         auth=ADMIN_CREDENTIALS
    #     ).json()

    #     if data['meta']['count'] == 1:
    #         return data['data'][0]
    #     else:
    #         return gen_registry(self._name)

    def get_registry(self):
        return self._registry

    def cleanup(self):
        del_registry(self._registry["pk"])


class ReusableRemoteContainer:
    def __init__(self, name, registry_pk, groups=None):
        self._ns_name = f"ee_ns_{name}"
        self._name = f"ee_remote_{name}"
        self._groups = groups or []
        self._registry_pk = registry_pk

        self._reset()

    def _reset(self):
        self._remote = gen_remote_container(f"{self._ns_name}/{self._name}", self._registry_pk)
        self._namespace = requests.put(
            f"{API_ROOT}_ui/v1/execution-environments/namespaces/{self._ns_name}/",
            json={
                "name": self._ns_name,
                "groups": self._groups

            },
            auth=ADMIN_CREDENTIALS
        ).json()
        self._container = requests.get(
            f"{API_ROOT}_ui/v1/execution-environments/repositories/{self._ns_name}/{self._name}/",
            auth=ADMIN_CREDENTIALS
        ).json()

    def get_container(self):
        return self._container

    def get_namespace(self):
        return self._namespace

    def get_remote(self):
        return self._remote

    def cleanup(self):
        del_container(f"{self._ns_name}/{self._name}")


class ReusableLocalContainer:
    def __init__(self, name, groups=None):
        self._ns_name = f"ee_ns_{name}"
        self._repo_name = f"ee_local_{name}"
        self._name = f"{self._ns_name}/{self._repo_name}"
        self._groups = groups or []

        self._reset()

    def _reset(self):
        podman_push(ADMIN_USER, ADMIN_PASSWORD, self._name)

        self._namespace = requests.put(
            f"{API_ROOT}_ui/v1/execution-environments/namespaces/{self._ns_name}/",
            json={
                "name": self._ns_name,
                "groups": self._groups

            },
            auth=ADMIN_CREDENTIALS
        ).json()

        self._container = requests.get(
            f"{API_ROOT}_ui/v1/execution-environments/repositories/{self._name}/",
            auth=ADMIN_CREDENTIALS
        ).json()

        self._manifest = requests.get(
            (
                f"{API_ROOT}_ui/v1/execution-environments/"
                f"repositories/{self._name}/_content/images/latest/"
            ),
            auth=ADMIN_CREDENTIALS
        ).json()

    def get_container(self):
        return self._container

    def get_namespace(self):
        return self._namespace

    def get_manifest(self):
        return self._manifest

    def cleanup(self):
        del_container(self._name)
