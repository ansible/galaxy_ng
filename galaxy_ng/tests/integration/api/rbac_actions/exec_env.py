import requests

from .utils import (
    API_ROOT,
    PULP_API_ROOT,
    SERVER,
    CONTAINER_IMAGE,
    assert_pass,
    gen_string,
    del_registry,
    del_container,
    gen_registry,
    gen_remote_container,
    cleanup_test_obj,
    podman_push,
    create_group
)

IMAGE_NAME = CONTAINER_IMAGE[0]


# REMOTES
def create_ee_remote(user, password, expect_pass, extra):
    registry = extra["registry"].get_registry()

    response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/",
        json={
            "name": gen_string(),
            "upstream_name": "foo",
            "registry": registry["id"],
        },
        auth=(user['username'], password),
    )

    cleanup_test_obj(response, "name", del_container)

    assert_pass(expect_pass, response.status_code, 201, 403)


def update_ee_remote(user, password, expect_pass, extra):
    remote = extra["remote_ee"].get_remote()
    remote["include_tags"] = ["latest"]

    response = requests.put(
        f"{API_ROOT}_ui/v1/execution-environments/remotes/{remote['id']}/",
        json=remote,
        auth=(user['username'], password),
    )

    assert_pass(expect_pass, response.status_code, 200, 403)


def sync_remote_ee(user, password, expect_pass, extra):
    container = extra["remote_ee"].get_container()

    response = requests.post(
        f'{API_ROOT}v3/plugin/execution-environments/repositories/'
        f'{container["name"]}/_content/sync/',
        auth=(user['username'], password)
    )
    assert_pass(expect_pass, response.status_code, 202, 403)

# REGISTRIES
def delete_ee_registry(user, password, expect_pass, extra):
    registry = gen_registry(gen_string())

    response = requests.delete(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{registry['id']}/",
        auth=(user['username'], password),
    )

    del_registry(registry["id"])

    assert_pass(expect_pass, response.status_code, 204, 403)


def index_ee_registry(user, password, expect_pass, extra):
    registry = extra["registry"].get_registry()

    response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{registry['id']}/index/",
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 400, 403)


def update_ee_registry(user, password, expect_pass, extra):
    registry = extra["registry"].get_registry()

    registry['rate_limit'] = 2

    response = requests.put(
        f"{API_ROOT}_ui/v1/execution-environments/registries/{registry['id']}/",
        json=registry,
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def create_ee_registry(user, password, expect_pass, extra):
    response = requests.post(
        f"{API_ROOT}_ui/v1/execution-environments/registries/",
        json={
            "name": gen_string(),
            "url": "http://example.com",
        },
        auth=(user['username'], password),
    )

    cleanup_test_obj(response, "id", del_registry)

    assert_pass(expect_pass, response.status_code, 201, 403)


# EXECUTION ENVIRONMENTS
def delete_ee(user, password, expect_pass, extra):
    registry = extra["registry"].get_registry()

    name = gen_string()
    gen_remote_container(name, registry["id"])

    response = requests.delete(
        f"{API_ROOT}v3/plugin/execution-environments/repositories/{name}/",
        auth=(user['username'], password),
    )

    del_container(name)

    assert_pass(expect_pass, response.status_code, 202, 403)


def change_ee_description(user, password, expect_pass, extra):
    container = extra["remote_ee"].get_container()

    response = requests.patch(
        f"{PULP_API_ROOT}distributions/container/container/{container['id']}/",
        json={
            "description": "hello world",
        },
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 202, 403)


def change_ee_readme(user, password, expect_pass, extra):
    container = extra["remote_ee"].get_container()

    url = (
        f"{API_ROOT}v3/plugin/execution-environments/repositories/"
        f"{container['name']}/_content/readme/"
    )
    response = requests.put(
        url,
        json={"text": "Praise the readme!"},
        auth=(user['username'], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def ee_namespace_list_roles(user, password, expect_pass, extra):
    pulp_href = extra["local_ee"].get_namespace()['pulp_href']

    PULP_CONTAINER_NAMESPACE = f"{SERVER}{pulp_href}"
    response = requests.get(
        f"{PULP_CONTAINER_NAMESPACE}list_roles/",
        auth=(user['username'], password)
    )

    assert_pass(expect_pass, response.status_code, 200, 403)


def ee_namespace_my_permissions(user, password, expect_pass, extra):
    pulp_href = extra["local_ee"].get_namespace()['pulp_href']

    PULP_CONTAINER_NAMESPACE = f"{SERVER}{pulp_href}"
    response = requests.get(
        f"{PULP_CONTAINER_NAMESPACE}my_permissions/",
        auth=(user['username'], password)
    )

    assert_pass(expect_pass, response.status_code, 200, 403)


def ee_namespace_add_role(user, password, expect_pass, extra):
    pulp_href = extra["local_ee"].get_namespace()['pulp_href']
    group_name = create_group(gen_string())["name"]

    PULP_CONTAINER_NAMESPACE = f"{SERVER}{pulp_href}"
    response = requests.post(
        f"{PULP_CONTAINER_NAMESPACE}add_role/",
        json={
            "role": "galaxy.execution_environment_admin",
            "groups": [group_name]
        },
        auth=(user['username'], password)
    )

    assert_pass(expect_pass, response.status_code, 201, 403)


def ee_namespace_remove_role(user, password, expect_pass, extra):
    pulp_href = extra["local_ee"].get_namespace()['pulp_href']

    PULP_CONTAINER_NAMESPACE = f"{SERVER}{pulp_href}"
    response = requests.post(
        f"{PULP_CONTAINER_NAMESPACE}remove_role/",
        json={
            "role": "galaxy.execution_environment_admin"
        },
        auth=(user['username'], password)
    )

    assert_pass(expect_pass, response.status_code, 201, 403)


def create_ee_local(user, password, expect_pass, extra):
    name = gen_string()
    return_code = podman_push(user['username'], password, name)

    if return_code == 0:
        del_container(name)

    if expect_pass:
        assert return_code == 0
    else:
        assert return_code != 0


def create_ee_in_existing_namespace(user, password, expect_pass, extra):
    namespace = extra["local_ee"].get_namespace()["name"]
    name = f"{namespace}/{gen_string()}"

    return_code = podman_push(user['username'], password, name)

    if return_code == 0:
        del_container(name)

    if expect_pass:
        assert return_code == 0
    else:
        assert return_code != 0


def push_updates_to_existing_ee(user, password, expect_pass, extra):
    container = extra["local_ee"].get_container()["name"]
    tag = gen_string()

    return_code = podman_push(user['username'], password, container, tag=tag)

    if expect_pass:
        assert return_code == 0
    else:
        assert return_code != 0


def change_ee_tags(user, password, expect_pass, extra):
    manifest = extra["local_ee"].get_manifest()
    repo_pk = extra["local_ee"].get_container()["pulp"]["repository"]["id"]
    tag = gen_string()

    response = requests.post(
        f'{PULP_API_ROOT}repositories/container/container-push/{repo_pk}/tag/',
        json={
            'digest': manifest['digest'],
            'tag': tag
        },
        auth=(user['username'], password)
    )

    assert_pass(expect_pass, response.status_code, 202, 403)
