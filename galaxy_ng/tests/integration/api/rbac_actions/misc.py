import requests
from .utils import PULP_API_ROOT, assert_pass


# Tasks
def view_tasks(user, password, expect_pass, extra):
    response = requests.get(
        f"{PULP_API_ROOT}tasks/",
        auth=(user['username'], password)
    )
    assert_pass(expect_pass, response.status_code, 200, 403)
