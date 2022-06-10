import requests
from .utils import PULP_API_ROOT


# Tasks
def view_tasks(user, password, expect_pass):
    response = requests.get(
        f"{PULP_API_ROOT}tasks/",
        auth=(user['username'], password)
    )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403
