import requests
from .utils import (
    ADMIN_CREDENTIALS,
    API_ROOT,
    NAMESPACE,
    PULP_API_ROOT,
    gen_string
)


# Groups
def view_groups(user, password):
    response = requests.get(
        f"{API_ROOT}_ui/v1/groups/",
        auth=(user['username'], password)
    )
    if response.status_code == 200:
        return True
    elif response.status_code == 403:
        return False


def delete_groups(user, password):
    # create a group to delete
    response = requests.post(
        f"{API_ROOT}_ui/v1/groups/",
        json={"name": f"{NAMESPACE}_group_{gen_string()}"},
        auth=ADMIN_CREDENTIALS
    )
    group_id = response.json()["id"]

    response = requests.delete(
        f"{API_ROOT}_ui/v1/groups/{group_id}/",
        auth=ADMIN_CREDENTIALS
    )
    if response.status_code == 204:
        return True
    elif response.status_code == 403:
        return False


# rbac_roles_user_wskfjimbdm
def add_groups(user, password):
    response = requests.post(
        f"{API_ROOT}_ui/v1/groups/",
        json={"name": f"{NAMESPACE}_group_{gen_string()}"},
        auth=(user["username"], password)
    )
    if response.status_code == 201:
        return True
    elif response.status_code == 403:
        return False


def change_groups(user, password):
    # create a group to change
    response = requests.post(
        f"{API_ROOT}_ui/v1/groups/",
        json={"name": f"{NAMESPACE}_group_{gen_string()}"},
        auth=(user["username"], password)
    )
    group_id = response.json()["id"]

    response = requests.patch(
        f"{PULP_API_ROOT}groups/{group_id}/",
        json={"name": f"{NAMESPACE}_group_{gen_string()}"},
        auth=(user["username"], password),
    )

    if response.status_code == 200:
        return True
    elif response.status_code == 403:
        return False


# Users
def view_users(user, password):
    response = requests.get(
        f"{API_ROOT}_ui/v1/users/",
        auth=(user["username"], password),
    )
    if response.status_code == 200:
        return True
    elif response.status_code == 403:
        return False


def delete_users(user, password):
    # Add user to delete
    response = requests.post(
        f"{API_ROOT}_ui/v1/users/",
        json={
            "username": f"{NAMESPACE}_username_{gen_string()}",
            "first_name": "",
            "last_name": "",
            "email": "",
            "group": "",
            "password": password,
            "description": "",
        },
        auth=ADMIN_CREDENTIALS,
    )
    user_id = response.json()["id"]
    # Delete user
    response = requests.delete(
        f"{API_ROOT}_ui/v1/users/{user_id}/",
        auth=(user["username"], password),
    )
    if response.status_code == 204:
        return True
    elif response.status_code == 403:
        return False


def add_users(user, password):
    response = requests.post(
        f"{API_ROOT}_ui/v1/users/",
        json={
            "username": f"{NAMESPACE}_username_{gen_string()}",
            "first_name": "",
            "last_name": "",
            "email": "",
            "group": "",
            "password": password,
            "description": "",
        },
        auth=(user["username"], password),
    )
    if response.status_code == 201:
        return True
    elif response.status_code == 403:
        return False


def change_users(user, password):
    # Add user to change
    response = requests.post(
        f"{API_ROOT}_ui/v1/users/",
        json={
            "username": f"{NAMESPACE}_username_{gen_string()}",
            "first_name": "first",
            "last_name": "",
            "email": "",
            "group": "",
            "password": password,
            "description": "",
        },
        auth=ADMIN_CREDENTIALS,
    )
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
            "password": password,
            "description": "",
        },
        auth=(user["username"], password),
    )
    if response.status_code == 200:
        return True
    elif response.status_code == 403:
        return False


# Roles
def add_role(user, password):
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

    if response.status_code == 201:
        return True
    elif response.status_code == 403:
        return False


def view_role(user, password):
    response = requests.get(
        f'{PULP_API_ROOT}roles/',
        auth=(user["username"], password),
    )

    if response.status_code == 200:
        return True
    elif response.status_code == 403:
        return False


def delete_role(user, password):
    # Add role to delete
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
        auth=ADMIN_CREDENTIALS,
    )
    role_id = response.json()['pulp_href'].split('/')[-2]
    # Delete role
    response = requests.delete(
        f'{PULP_API_ROOT}roles/{role_id}/',
        auth=(user["username"], password),
    )

    if response.status_code == 204:
        return True
    elif response.status_code == 403:
        return False


def change_role(user, password):
    # Add role to change
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
        auth=ADMIN_CREDENTIALS,
    )
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
    if response.status_code == 200:
        return True
    elif response.status_code == 403:
        return False
