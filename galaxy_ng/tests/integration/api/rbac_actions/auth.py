import requests

from .utils import ADMIN_PASSWORD, ADMIN_USER, PASSWORD as UTIL_PASSWORD
from .utils import (
    ADMIN_CREDENTIALS,
    API_ROOT,
    NAMESPACE,
    PULP_API_ROOT,
    group_exists,
    role_exists,
    user_exists
)


# Groups
def view_groups(user, password, expect_pass):
    response = requests.get(
        f"{API_ROOT}_ui/v1/groups/",
        auth=(user['username'], password)
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def delete_groups(user, password, expect_pass):
    # create a group to delete
    if group_exists():
        response = group_exists()
    else:
        response = add_groups(ADMIN_USER, ADMIN_PASSWORD, True)
    group_id = response["id"]
    # delete group
    response = requests.delete(
        f"{API_ROOT}_ui/v1/groups/{group_id}/",
        auth=(user['username'], password)
    )
    if expect_pass:
        assert response.status_code == 204
    else:
        assert response.status_code == 403
        response = requests.delete(
            f"{API_ROOT}_ui/v1/groups/{group_id}/",
            auth=ADMIN_CREDENTIALS
        )


def add_groups(user, password, expect_pass):
    if group_exists():
        response = group_exists()
        requests.delete(
            f"{API_ROOT}_ui/v1/groups/{response['id']}/",
            auth=ADMIN_CREDENTIALS,
        )
    response = requests.post(
        f"{API_ROOT}_ui/v1/groups/",
        json={"name": f"{NAMESPACE}_group"},
        auth=(user["username"], password)
    )
    if expect_pass:
        assert response.status_code == 201
    else:
        assert response.status_code == 403
    return response.json()


def change_groups(user, password, expect_pass):
    if group_exists():
        response = group_exists()
    else:
        response = add_groups(ADMIN_USER, ADMIN_PASSWORD, True)
    group_id = response["id"]
    # Change group
    response = requests.patch(
        f"{PULP_API_ROOT}groups/{group_id}/",
        json={"name": f"{NAMESPACE}_group_2"},
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403
    response = requests.delete(
        f"{API_ROOT}_ui/v1/groups/{group_id}/",
        auth=ADMIN_CREDENTIALS
    )


# Users
def view_users(user, password, expect_pass):
    response = requests.get(
        f"{API_ROOT}_ui/v1/users/",
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def add_users(user, password, expect_pass):
    if user_exists():
        response = user_exists()
        requests.delete(
            f"{API_ROOT}_ui/v1/users/{response['id']}/",
            auth=ADMIN_CREDENTIALS,
        )
    response = requests.post(
        f"{API_ROOT}_ui/v1/users/",
        json={
            "username": f"{NAMESPACE}_user",
            "first_name": "",
            "last_name": "",
            "email": "",
            "group": "",
            "password": UTIL_PASSWORD,
            "description": "",
        },
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 201
    else:
        assert response.status_code == 403
    return response.json()


def change_users(user, password, expect_pass):
    if user_exists():
        response = user_exists()
    else:
        response = add_users(ADMIN_USER, ADMIN_PASSWORD, True)
    user_id = response["id"]
    # Change user
    response = requests.put(
        f"{API_ROOT}_ui/v1/users/{user_id}/",
        json={
            "username": f"{NAMESPACE}_user",
            "first_name": "new_first",
            "last_name": "",
            "email": "",
            "group": "",
            "password": UTIL_PASSWORD,
            "description": "",
        },
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403
    # Cleanup
    response = requests.delete(
        f"{API_ROOT}_ui/v1/users/{user_id}/",
        auth=(user["username"], password),
    )


def delete_users(user, password, expect_pass):
    if user_exists():
        response = user_exists()
    else:
        response = add_users(ADMIN_USER, ADMIN_PASSWORD, True)
    user_id = response["id"]
    # Delete user
    response = requests.delete(
        f"{API_ROOT}_ui/v1/users/{user_id}/",
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 204
    else:
        assert response.status_code == 403


def add_role(user, password, expect_pass):
    if role_exists():
        response = role_exists()
        role_id = response['pulp_href'].split('/')[-2]
        requests.delete(
            f"{PULP_API_ROOT}roles/{role_id}/",
            auth=ADMIN_CREDENTIALS,
        )
    response = requests.post(
        f"{PULP_API_ROOT}roles/",
        json={
            "name": f"{NAMESPACE}_role",
            "permissions": [
                "galaxy.add_group",
                "galaxy.change_group",
                "galaxy.delete_group",
                "galaxy.view_group",
            ],
        },
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 201
    else:
        assert response.status_code == 403
    return response.json()


def view_role(user, password, expect_pass):
    response = requests.get(
        f'{PULP_API_ROOT}roles/',
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def delete_role(user, password, expect_pass):
    if role_exists():
        response = role_exists()
    else:
        response = add_role(ADMIN_USER, ADMIN_PASSWORD, True)
    role_id = response['pulp_href'].split('/')[-2]
    # Delete role
    response = requests.delete(
        f'{PULP_API_ROOT}roles/{role_id}/',
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 204
    else:
        assert response.status_code == 403


def change_role(user, password, expect_pass):
    if role_exists():
        response = role_exists()
    else:
        response = add_role(ADMIN_USER, ADMIN_PASSWORD, True)
    role_id = response['pulp_href'].split('/')[-2]
    # Change role
    response = requests.patch(
        f'{PULP_API_ROOT}roles/{role_id}/',
        json={
            "name": f"{NAMESPACE}_role",
            "permissions": [
                "galaxy.add_user",
                "galaxy.change_user",
                "galaxy.view_user",
            ],
        },
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403
