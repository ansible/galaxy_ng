import requests

from .utils import ADMIN_PASSWORD, ADMIN_USER, PASSWORD as UTIL_PASSWORD
from .utils import (
    ADMIN_CREDENTIALS,
    API_ROOT,
    NAMESPACE,
    PULP_API_ROOT,
    gen_string,
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
    response = add_groups(ADMIN_USER, ADMIN_PASSWORD, True, cleanup=False)
    group_id = response.json()["id"]
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


def add_groups(user, password, expect_pass, cleanup=True):
    response = requests.post(
        f"{API_ROOT}_ui/v1/groups/",
        json={"name": f"{NAMESPACE}_group_{gen_string()}"},
        auth=(user["username"], password)
    )
    if expect_pass:
        assert response.status_code == 201
    else:
        assert response.status_code == 403
    if response.status_code != 403:
        group_id = response.json()["id"]
        if cleanup:
            response = requests.delete(
                f"{API_ROOT}_ui/v1/groups/{group_id}/",
                auth=ADMIN_CREDENTIALS
            )
        else:
            return response


def change_groups(user, password, expect_pass):
    # Create a group to change
    response = add_groups(ADMIN_USER, ADMIN_PASSWORD, True, cleanup=False)
    group_id = response.json()["id"]
    # Change group
    response = requests.patch(
        f"{PULP_API_ROOT}groups/{group_id}/",
        json={"name": f"{NAMESPACE}_group_{gen_string()}"},
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


def delete_users(user, password, expect_pass):
    # Add user to delete
    response = add_users(ADMIN_USER, ADMIN_PASSWORD, True, cleanup=False)
    user_id = response.json()["id"]
    # Delete user
    response = requests.delete(
        f"{API_ROOT}_ui/v1/users/{user_id}/",
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 204
    else:
        assert response.status_code == 403
        # Cleanup
        response = requests.delete(
            f"{API_ROOT}_ui/v1/users/{user_id}/",
            auth=(user["username"], password),
        )


def add_users(user, password, expect_pass, cleanup=True):
    response = requests.post(
        f"{API_ROOT}_ui/v1/users/",
        json={
            "username": f"{NAMESPACE}_username_{gen_string()}",
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
    if response.status_code != 403:
        user_id = response.json()["id"]
        if cleanup:
            response = requests.delete(
                f"{API_ROOT}_ui/v1/users/{user_id}/",
                auth=(user["username"], password),
            )
        else:
            return response


def change_users(user, password, expect_pass):
    # Add user to change
    response = add_users(ADMIN_USER, ADMIN_PASSWORD, True, cleanup=False)
    user_id = response.json()["id"]
    response.json()
    # Change user
    response = requests.put(
        f"{API_ROOT}_ui/v1/users/{user_id}/",
        json={
            "username": f"{NAMESPACE}_username_{gen_string()}",
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


def add_role(user, password, expect_pass, cleanup=True):
    response = requests.post(
        f"{PULP_API_ROOT}roles/",
        json={
            "name": f"{NAMESPACE}_role_{gen_string()}",
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
    if response.status_code != 403:
        if cleanup:
            requests.delete(
                f'{PULP_API_ROOT}roles/{response.json()["pulp_href"]}/',
                auth=ADMIN_CREDENTIALS
            )
        else:
            return response


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
    # Add role to delete
    create_response = add_role(ADMIN_USER, ADMIN_PASSWORD, True, cleanup=False)
    role_id = create_response.json()['pulp_href'].split('/')[-2]
    # Delete role
    response = requests.delete(
        f'{PULP_API_ROOT}roles/{role_id}/',
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 204
    else:
        assert response.status_code == 403
        # Cleanup
        requests.delete(
            f'{PULP_API_ROOT}roles/{role_id}/',
            auth=ADMIN_CREDENTIALS
        )


def change_role(user, password, expect_pass):
    # Add role to change
    response = add_role(ADMIN_USER, ADMIN_PASSWORD, True, cleanup=False)
    role_id = response.json()['pulp_href'].split('/')[-2]
    # Change role
    response = requests.patch(
        f'{PULP_API_ROOT}roles/{role_id}/',
        json={
            "name": f"{NAMESPACE}_role_{gen_string()}",
            "permissions": [
                "galaxy.add_user",
                "galaxy.change_user",
                "galaxy.delete_user",
                "galaxy.view_user",
            ],
        },
        auth=(user["username"], password),
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403
    # Cleanup
    requests.delete(
        f'{PULP_API_ROOT}roles/{role_id}/',
        auth=ADMIN_CREDENTIALS
    )
