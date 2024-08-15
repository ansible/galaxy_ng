import logging
import pytest
from ..integration.utils.iqe_utils import (
    get_ansible_config, get_galaxy_client
)

MARKER_CONFIG = """
qa: Mark tests to run in the vortex job.
galaxyapi_smoke: Smoke tests for galaxy-api backend.
deployment_standalone: Tests that should not run against the Insights version of Hub.
deployment_cloud: Tests that should not run against the standalone version of Hub.
deployment_community: Tests relevant to the community deployment profile.
cli: Tests that shell out to the real ansible-galaxy cli.
ui: Tests that navigate the UI via selenium.
ui_standalone: UI tests that only work in standalone mode.
smoke: Same as galaxyapi_smoke?
prod_status: For checking prod?
busted: Doesn't work yet.
stage_health: For checking stage?
namespace: Tests that manipulate namespaces.
certification: Related to certification.
collection_move: Related to moving collection versions.
collection_delete: Deletes collections.
collection_version_delete: Deletes collections versions.
collection_signing: Related to collection signing.
delete: Tests for deleting objects.
move: Related to the move api.
synclist: Related to synclist object and synclist repo.
openapi: Checks the openapi schema and routes.
openapi_generate_bindings: Verifies pulp client bindings generator
package: tests for the pip packaging
api_ui: tests for the _ui v1 api
importer: tests related checks in galaxy-importer
pulp_api: tests related to the pulp api endpoints
ldap: tests related to the ldap integration
role: Related to RBAC Roles
rbac_roles: Tests checking Role permissions
group: Related to Groups
slow_in_cloud: tests that take too long to be run against stage
max_hub_version: This marker takes an argument that indicates the maximum hub version
min_hub_version: This marker takes an argument that indicates the minimum hub version
iqe_rbac_test: imported iqe tests checking role permissions
iqe_ldap: imported iqe tests checking ldap integration
sync: sync tests against stage
certified_sync: sync tests container against container
auto_approve: run tests that require AUTO_APPROVE to be set to true
private_repos: run tests verifying private repositories
rbac_repos: tests verifying rbac roles on custom repositories
x_repo_search: tests verifying cross-repo search endpoint
repositories: tests verifying custom repositories
all: tests that are unmarked and should pass in all deployment modes
galaxy_stage_ansible: tests that run against galaxy-stage.ansible.com
installer_smoke_test: smoke tests to validate AAP installation (VM)
load_data: tests that load data that will be verified after upgrade or backup/restore
verify_data: tests that verify the data previously loaded by load_data test
skip_in_gw: tests that need to be skipped if hub is behind the gateway (temporary)
"""

logger = logging.getLogger(__name__)

def pytest_configure(config):
    for line in MARKER_CONFIG.split('\n'):
        if not line:
            continue
        config.addinivalue_line('markers', line)

@pytest.fixture(scope="session")
def ansible_config():
    return get_ansible_config()

@pytest.fixture(scope="session")
def galaxy_client(ansible_config):
    return get_galaxy_client(ansible_config)
