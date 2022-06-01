import requests
from .utils import (
    ADMIN_CREDENTIALS,
    API_ROOT,
    NAMESPACE,
    PULP_API_ROOT,
    gen_string
)


def create_collection_namespace(user, password, expect_pass):
    response = requests.post(
        f"{API_ROOT}_ui/v1/namespaces/",
        json={
            "name": f"{NAMESPACE}_namespace_{gen_string()}",
            "groups": [{
                "name": "system:partner-engineers",
                "object_roles": ["galaxy.content_admin"]
            }],
        },
        auth=(user['username'], password),
    )
    if expect_pass:
        assert response.status_code == 201
    else:
        assert response.status_code == 403


def change_collection_namespace(user, password, expect_pass):
    # Create namespace to change
    response = requests.post(
        f"{API_ROOT}_ui/v1/namespaces/",
        json={
            "name": f"{NAMESPACE}_namespace_{gen_string()}",
            "groups": [{
                "name": "system:partner-engineers",
                "object_roles": ["galaxy.content_admin"]
            }],
        },
        auth=(user['username'], password),
    )
    if response.status_code != 403:
        namespace_name = response.json()["name"]
        namespace_groups = response.json()["groups"]
        response = requests.put(
            f"{API_ROOT}_ui/v1/namespaces/{namespace_name}/",
            json={
                "name": namespace_name,
                "groups": namespace_groups,
                "description": "Praise the description!",
            },
            auth=(user['username'], password),
        )
    if expect_pass:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def delete_collection_namespace(user, password, expect_pass):
    # Create namespace to delete
    response = requests.post(
        f"{API_ROOT}_ui/v1/namespaces/",
        json={
            "name": f"{NAMESPACE}_namespace_{gen_string()}",
            "groups": [{
                "name": "system:partner-engineers",
                "object_roles": ["galaxy.content_admin"]
            }],
        },
        auth=(user['username'], password),
    )
    if response.status_code != 403:
        namespace_name = response.json()["name"]
        response = requests.delete(
            f"{API_ROOT}_ui/v1/namespaces/{namespace_name}/",
            auth=(user['username'], password),
        )
    if expect_pass:
        assert response.status_code == 204
    else:
        assert response.status_code == 403


def upload_collection_to_namespace(user, password, expect_pass):
    pass


def configure_collection_sync(user, password, expect_pass):
    # PUT /api/automation-hub/content/community/v3/sync/config/
    pass


def launch_collection_sync(user, password, expect_pass):
    # POST /api/automation-hub/content/community/v3/sync/
    pass


def view_sync_configuration(user, password, expect_pass):
    # GET /api/automation-hub/content/community/v3/sync/config/
    pass


def approve_reject_collections(user, password, expect_pass):
    # upload collection
    # approve collection
    pass


def deprecate_collections(user, password, expect_pass):
    # PATCH /api/automation-hub/v3/plugin/ansible/content/community/collections/index/geerlingguy/php_roles/
    pass


def undeprecate_collections(user, password, expect_pass):
    # PATCH /api/automation-hub/v3/plugin/ansible/content/community/collections/index/geerlingguy/php_roles/
    pass
