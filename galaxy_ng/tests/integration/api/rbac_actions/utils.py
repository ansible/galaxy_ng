import random
import requests
import string
import time
from urllib.parse import urljoin

from ansible.galaxy.api import GalaxyError

NAMESPACE = "rbac_roles"
PASSWORD = "p@ssword!"
ADMIN_CREDENTIALS = ("admin", "admin")
API_ROOT = "http://localhost:5001/api/automation-hub/"
PULP_API_ROOT = "http://localhost:5001/api/automation-hub/pulp/api/v3/"


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


def wait_for_task(resp, path, timeout=300):
    ready = False
    url = urljoin(f"{API_ROOT}{path}", f'{resp.json()["task"]}/')
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
