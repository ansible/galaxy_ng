import requests

from .utils import (
    API_ROOT,
    NAMESPACE,
    PULP_API_ROOT,
    PASSWORD,
    SERVER,
    assert_pass,
    del_user,
    del_role,
    del_group,
    create_group,
    create_user,
    create_role,
    gen_string
)


def view_groups(user, password, expect_pass, extra):
    response = requests.get(
        f"{API_ROOT}_ui/v1/groups/",
        auth=(user['username'], password)
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def delete_groups(user, password, expect_pass, extra):
    g = create_group(gen_string())
    # delete group
    response = requests.delete(
        f"{API_ROOT}_ui/v1/groups/{g['id']}/",
        auth=(user['username'], password)
    )

    del_group(g['id'])

    assert_pass(expect_pass, response.status_code, 204, 403)


def add_groups(user, password, expect_pass, extra):
    response = requests.post(
        f"{API_ROOT}_ui/v1/groups/",
        json={"name": f"{NAMESPACE}_group"},
        auth=(user["username"], password)
    )

    data = response.json()

    if "id" in data:
        del_group(data["id"])

    assert_pass(expect_pass, response.status_code, 201, 403)
    return response.json()


def change_groups(user, password, expect_pass, extra):
    g = create_group(gen_string())

    response = requests.post(
        f"{PULP_API_ROOT}groups/{g['id']}/roles/",
        json={
            "content_object": None,
            "role": "galaxy.content_admin",
        },
        auth=(user["username"], password),
    )

    del_group(g['id'])

    assert_pass(expect_pass, response.status_code, 201, 403)


def view_users(user, password, expect_pass, extra):
    response = requests.get(
        f"{API_ROOT}_ui/v1/users/",
        auth=(user["username"], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def add_users(user, password, expect_pass, extra):
    response = requests.post(
        f"{API_ROOT}_ui/v1/users/",
        json={
            "username": gen_string(),
            "first_name": "",
            "last_name": "",
            "email": "",
            "group": "",
            "password": PASSWORD,
            "description": "",
        },
        auth=(user["username"], password),
    )

    data = response.json()

    if "id" in data:
        del_user(data["id"])

    assert_pass(expect_pass, response.status_code, 201, 403)


def change_users(user, password, expect_pass, extra):
    new_user = create_user(gen_string(), PASSWORD)
    new_user["first_name"] = "foo"

    response = requests.put(
        f"{API_ROOT}_ui/v1/users/{new_user['id']}/",
        json=new_user,
        auth=(user["username"], password),
    )

    del_user(new_user["id"])

    assert_pass(expect_pass, response.status_code, 200, 403)


def delete_users(user, password, expect_pass, extra):
    new_user = create_user(gen_string(), PASSWORD)
    # Delete user
    response = requests.delete(
        f"{API_ROOT}_ui/v1/users/{new_user['id']}/",
        auth=(user["username"], password),
    )

    del_user(new_user['id'])

    assert_pass(expect_pass, response.status_code, 204, 403)


def add_role(user, password, expect_pass, extra):
    response = requests.post(
        f"{PULP_API_ROOT}roles/",
        json={
            "name": gen_string(),
            "permissions": [
                "galaxy.add_group",
                "galaxy.change_group",
                "galaxy.delete_group",
                "galaxy.view_group",
            ],
        },
        auth=(user["username"], password),
    )

    data = response.json()

    if "pulp_href" in data:
        del_role(data["pulp_href"])

    assert_pass(expect_pass, response.status_code, 201, 403)


def view_role(user, password, expect_pass, extra):
    response = requests.get(
        f'{PULP_API_ROOT}roles/',
        auth=(user["username"], password),
    )
    assert_pass(expect_pass, response.status_code, 200, 403)


def delete_role(user, password, expect_pass, extra):
    r = create_role(gen_string())

    response = requests.delete(
        f'{SERVER}{r["pulp_href"]}',
        auth=(user["username"], password),
    )

    del_role(r["pulp_href"])

    assert_pass(expect_pass, response.status_code, 204, 403)


def change_role(user, password, expect_pass, extra):
    role = create_role(gen_string())

    role["permissions"] = [
        "galaxy.add_user",
        "galaxy.change_user",
        "galaxy.view_user",
    ]

    response = requests.patch(
        f'{SERVER}{role["pulp_href"]}',
        json=role,
        auth=(user["username"], password),
    )

    del_role(role["pulp_href"])

    assert_pass(expect_pass, response.status_code, 200, 403)
