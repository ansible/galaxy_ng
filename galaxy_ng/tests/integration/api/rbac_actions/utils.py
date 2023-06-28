import requests
import time
import subprocess
from urllib.parse import urljoin
from galaxy_ng.tests.integration.utils import (
    build_collection,
    upload_artifact,
    get_client,
    wait_for_task as wait_for_task_fixtures,
    TaskWaitingTimeout,
    gen_string,
    wait_for_all_tasks as wait_for_all_tasks_fixtures,
    AnsibleDistroAndRepo
)
from galaxy_ng.tests.integration.conftest import AnsibleConfigFixture, get_ansible_config, \
    get_galaxy_client

from ansible.galaxy.api import GalaxyError

from galaxy_ng.tests.integration.utils.iqe_utils import is_ephemeral_env
from galaxykit.container_images import get_container, get_container_images_latest
ansible_config = get_ansible_config()
CLIENT_CONFIG = ansible_config("admin")
ADMIN_CLIENT = get_client(CLIENT_CONFIG)

ansible_config = get_ansible_config()
galaxy_client = get_galaxy_client(ansible_config)
if is_ephemeral_env():
    gc_admin = galaxy_client("partner_engineer", basic_token=True)
else:
    gc_admin = galaxy_client("admin", basic_token=False)

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

TEST_CONTAINER = "quay.io/libpod/alpine"

session = requests.Session()
session.verify = False


class InvalidResponse(Exception):
    pass


def assert_pass(expect_pass, code, pass_status, deny_status):
    if code not in (pass_status, deny_status):
        raise InvalidResponse(f'Invalid response status code: {code}')

    if expect_pass:
        assert code == pass_status
    else:
        assert code == deny_status


def create_group_for_user(user, role=None):
    name = f"{NAMESPACE}_group_{gen_string()}"

    g = create_group(name)

    session.post(
        f"{API_ROOT}_ui/v1/groups/{g['id']}/users/",
        json={"username": user["username"]},
        auth=ADMIN_CREDENTIALS
    )

    if role:
        add_group_role(g["pulp_href"], role)

    return g


def add_group_role(group_href, role, object_href=None):
    session.post(
        SERVER + group_href + "roles/",
        json={"role": role, "content_object": object_href},
        auth=ADMIN_CREDENTIALS
    )


def create_user(username, password):
    response = session.post(
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
            resp = session.get(url, auth=ADMIN_CREDENTIALS)
        except GalaxyError as e:
            if "500" not in str(e):
                raise
        else:
            ready = resp.json()["state"] not in ("running", "waiting")
        time.sleep(5)
    return resp


def wait_for_all_tasks():
    wait_for_all_tasks_fixtures(ADMIN_CLIENT)


def ensure_test_container_is_pulled():
    container_engine = CLIENT_CONFIG["container_engine"]
    cmd = [container_engine, "image", "exists", TEST_CONTAINER]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 1:
        cmd = [container_engine, "image", "pull", TEST_CONTAINER]
        rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert rc.returncode == 0


def podman_push(username, password, container, tag="latest"):
    ensure_test_container_is_pulled()
    container_engine = CLIENT_CONFIG["container_engine"]
    container_registry = CLIENT_CONFIG["container_registry"]

    new_container = f"{container_registry}/{container}:{tag}"
    tag_cmd = [container_engine, "image", "tag", TEST_CONTAINER, new_container]

    subprocess.run(tag_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if container_engine == "docker":
        login_cmd = ["docker", "login", "-u", username, "-p", password, container_registry]
        subprocess.run(login_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if container_engine == "podman":
        push_cmd = [
            container_engine,
            "push",
            "--creds",
            f"{username}:{password}",
            new_container,
            "--remove-signatures",
            "--tls-verify=false"]

    if container_engine == "docker":
        push_cmd = [
            container_engine,
            "push",
            new_container]

    rc = subprocess.run(push_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return rc.returncode


def del_user(pk):
    session.delete(
        f"{API_ROOT}_ui/v1/users/{pk}/",
        auth=(ADMIN_CREDENTIALS),
    )


def create_group(name):
    return session.post(
        f"{API_ROOT}_ui/v1/groups/",
        json={"name": name},
        auth=ADMIN_CREDENTIALS
    ).json()


def del_group(pk):
    return session.delete(
        f"{API_ROOT}_ui/v1/groups/{pk}/",
        auth=ADMIN_CREDENTIALS
    )


def create_role(name):
    return session.post(
        f"{PULP_API_ROOT}roles/",
        json={
            "name": name,
            "permissions": [],
        },
        auth=ADMIN_CREDENTIALS,
    ).json()


def del_role(href):
    session.delete(
        f"{SERVER}{href}",
        auth=ADMIN_CREDENTIALS
    )


def del_namespace(name):
    return session.delete(
        f"{API_ROOT}_ui/v1/namespaces/{name}/",
        auth=ADMIN_CREDENTIALS,
    )


def del_collection(name, namespace, repo="staging"):
    session.delete(
        f"{API_ROOT}v3/plugin/ansible/content/{repo}/collections/index/{namespace}/{name}/",
        auth=ADMIN_CREDENTIALS,
    )


def gen_namespace(name, groups=None):
    groups = groups or []

    resp = session.post(
        f"{API_ROOT}v3/namespaces/",
        json={
            "name": name,
            "groups": groups,
        },
        auth=ADMIN_CREDENTIALS,
    )

    assert resp.status_code == 201
    return resp.json()


def gen_collection(name, namespace):
    artifact = build_collection(
        name=name,
        namespace=namespace
    )

    ansible_config = AnsibleConfigFixture("admin", namespace=artifact.namespace)

    client = ADMIN_CLIENT

    wait_for_task_fixtures(client, upload_artifact(ansible_config, client, artifact))

    resp = session.get(
        f"{PULP_API_ROOT}content/ansible/collection_versions/?name={name}&namespace={namespace}",
        auth=ADMIN_CREDENTIALS
    )

    return resp.json()["results"][0]


def reset_remote():
    return session.put(
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
        wait_for_all_tasks()
        session.post(
            (
                f"{API_ROOT}v3/collections/{self._namespace_name}"
                f"/{self._collection_name}/versions/{self._collection['version']}"
                "/move/rejected/staging/"
            ),
            auth=ADMIN_CREDENTIALS,
        )
        session.post(
            (
                f"{API_ROOT}v3/collections/{self._namespace_name}"
                f"/{self._collection_name}/versions/{self._collection['version']}"
                "/move/published/staging/"
            ),
            auth=ADMIN_CREDENTIALS,
        )

    def _get_repo_href(self, name):
        return session.get(
            f"{PULP_API_ROOT}repositories/ansible/ansible/?name={name}",
            auth=ADMIN_CREDENTIALS
        ).json()["results"][0]["pulp_href"]

    def _reset_collection(self):
        wait_for_all_tasks()

        resp = session.get(
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

        session.patch(
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

    def __del__(self):
        self.cleanup()


def cleanup_test_obj(response, pk, del_func):
    data = response.json()

    if pk in data:
        del_func(pk)


def del_container(name):
    session.delete(
        f"{API_ROOT}v3/plugin/execution-environments/repositories/{name}/",
        auth=ADMIN_CREDENTIALS,
    )


def gen_remote_container(name, registry_pk):
    return session.post(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/",
        json={
            "name": name,
            "upstream_name": "foo",
            "registry": registry_pk,
        },
        auth=ADMIN_CREDENTIALS,
    ).json()


def del_registry(pk):
    session.delete(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{pk}/",
        auth=ADMIN_CREDENTIALS,
    )


def gen_registry(name):
    return session.post(
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

    def get_registry(self):
        return self._registry

    def cleanup(self):
        del_registry(self._registry["id"])

    def __del__(self):
        self.cleanup()


class ReusableAnsibleRepository(AnsibleDistroAndRepo):
    def __init__(self, name, is_staging, is_private=False, add_collection=False):
        repo_body = {}
        if is_staging:
            repo_body["pulp_labels"] = {"pipeline": "staging"}
        if is_private:
            repo_body["private"] = True
        super().__init__(
            ADMIN_CLIENT, name, repo_body=repo_body, distro_body=None)

        if add_collection:
            self._add_collection()

    def _add_collection(self):
        namespace = gen_namespace(gen_string())
        artifact = build_collection(
            name=gen_string(),
            namespace=namespace["name"]
        )

        server = API_ROOT + f"content/{self.get_distro()['base_path']}/"

        cmd = [
            "ansible-galaxy",
            "collection",
            "publish",
            "--api-key",
            ADMIN_TOKEN,
            "--server",
            server,
            artifact.filename
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.returncode == 0
        wait_for_all_tasks()


class ReusableRemoteContainer:
    def __init__(self, name, registry_pk):
        self._ns_name = f"ee_ns_{name}"
        self._name = f"ee_remote_{name}"
        self._registry_pk = registry_pk

        self._reset()

    def _reset(self):
        self._remote = gen_remote_container(f"{self._ns_name}/{self._name}", self._registry_pk)

        container = session.get(
            f"{API_ROOT}v3/plugin/execution-environments/"
            f"repositories/{self._ns_name}/{self._name}/",
            auth=ADMIN_CREDENTIALS
        ).json()

        namespace_id = container['namespace']['id']
        pulp_namespace_path = f"pulp/api/v3/pulp_container/namespaces/{namespace_id}"

        # get roles first
        roles = session.get(
            f"{API_ROOT}{pulp_namespace_path}/list_roles",
            auth=ADMIN_CREDENTIALS
        ).json()

        for role in roles['roles']:
            self.pulp_namespace = session.post(
                f"{API_ROOT}{pulp_namespace_path}/remove_role",
                json={
                    'role': role['role']
                },
                auth=ADMIN_CREDENTIALS
            )

        self._namespace = session.get(
            f"{API_ROOT}{pulp_namespace_path}",
            auth=ADMIN_CREDENTIALS
        ).json()

        self._container = session.get(
            f"{API_ROOT}v3/plugin/execution-environments/"
            f"repositories/{self._ns_name}/{self._name}/",
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

    def __del__(self):
        self.cleanup()


class ReusableLocalContainer:
    def __init__(self, name):
        self._ns_name = f"ee_ns_{name}"
        self._repo_name = f"ee_local_{name}"
        self._name = f"{self._ns_name}/{self._repo_name}"

        self._reset()

    def _reset(self):
        p = podman_push(ADMIN_USER, ADMIN_PASSWORD, self._name)

        # check if the podman push command succeeds
        assert p == 0
        # reset pulp_container/namespace
        # 1. get namespace pulp_id from repositories
        # 2. get roles in namespace
        # 3. remove roles and groups (clean container namespace)
        self._container = get_container(gc_admin, self._name)
        ns_r = gc_admin.get(f"pulp/api/v3/pulp_container/namespaces/?name={self._ns_name}")
        pulp_namespace_path = ns_r["results"][0]["pulp_href"]
        # get roles first
        roles = gc_admin.get(f"{pulp_namespace_path}list_roles")
        for role in roles["roles"]:
            body = {
                'role': role["role"]
            }
            gc_admin.post(path=f"{pulp_namespace_path}remove_role/", body=body)

        self._namespace = gc_admin.get(pulp_namespace_path)
        self._manifest = get_container_images_latest(gc_admin, self._name)

    def get_container(self):
        return self._container

    def get_namespace(self):
        return self._namespace

    def get_manifest(self):
        return self._manifest

    def cleanup(self):
        del_container(self._name)


def add_role_common(user, password, expect_pass, pulp_href, role):
    group_name = create_group(gen_string())["name"]

    response = session.post(
        f"{SERVER}{pulp_href}add_role/",
        json={
            "role": role,
            "groups": [group_name]
        },
        auth=(user['username'], password)
    )

    assert_pass(expect_pass, response.status_code, 201, 403)


def remove_role_common(user, password, expect_pass, pulp_href, role):
    response = session.post(
        f"{SERVER}{pulp_href}remove_role/",
        json={
            "role": role
        },
        auth=(user['username'], password)
    )

    assert_pass(expect_pass, response.status_code, 201, 403)


def list_roles_common(user, password, expect_pass, pulp_href):
    response = session.get(
        f"{SERVER}{pulp_href}list_roles/",
        auth=(user['username'], password)
    )

    assert_pass(expect_pass, response.status_code, 200, 403)
