import requests
from .utils import (
    ADMIN_CREDENTIALS,
    API_ROOT,
    NAMESPACE,
    PULP_API_ROOT,
    gen_string
)


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


def cancel_tasks(user, password, expect_pass):
    pass
    # Create a remote registry
    # Create an execution environment
    # Sync execution environment
    # task_id = None
    # if expect_pass:
    #     assert response.status_code == 204
    # else:
    #     assert response.status_code == 403
