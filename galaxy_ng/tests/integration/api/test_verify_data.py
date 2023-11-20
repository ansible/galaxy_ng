import logging
import pytest

from galaxy_ng.tests.integration.conftest import is_hub_4_7_or_higher
from galaxy_ng.tests.integration.utils.iqe_utils import is_upgrade_from_aap23_hub46, \
    galaxy_auto_sign_collections
from galaxy_ng.tests.integration.utils.repo_management_utils import search_collection_endpoint
from galaxykit.collections import collection_info
from galaxykit.groups import get_group_id
from galaxykit.namespaces import get_namespace
from galaxykit.registries import get_registry_pk
from galaxykit.remotes import view_remotes
from galaxykit.repositories import get_repository_href
from galaxykit.roles import get_role
from galaxykit.users import get_user

logger = logging.getLogger(__name__)

SKIP_MESSAGE = "Load data stage was run on AAP 2.3, without repository management"


class TestVerifyData:

    @pytest.mark.min_hub_version("4.6dev")
    @pytest.mark.verify_data
    def test_verify_data_users(self, galaxy_client, data):
        """
        Test that verifies the data previously loaded by test_load_data
        """
        gc = galaxy_client("admin")
        for expected_user in data["users"]:
            actual_user = get_user(gc, expected_user["username"])
            assert expected_user["username"] == actual_user["username"]
            assert expected_user["email"] == actual_user["email"]
            assert expected_user["is_superuser"] == actual_user["is_superuser"]
            assert expected_user["group"] in str(actual_user["groups"])

    @pytest.mark.min_hub_version("4.6dev")
    @pytest.mark.verify_data
    def test_verify_data_ns(self, galaxy_client, data):
        """
        Test that verifies the data previously loaded by test_load_data
        """
        gc = galaxy_client("admin")
        for expected_ns in data["namespaces"]:
            actual_ns = get_namespace(gc, expected_ns["name"])
            assert expected_ns["name"] == actual_ns["name"]
            assert expected_ns["group"] in str(actual_ns["groups"])

    @pytest.mark.min_hub_version("4.6dev")
    @pytest.mark.verify_data
    def test_verify_data_collections(self, galaxy_client, data, ansible_config):
        """
        Test that verifies the data previously loaded by test_load_data
        """
        gc = galaxy_client("admin")
        for expected_col in data["collections"]:
            if (expected_col["repository"]
                != "published" and not is_hub_4_7_or_higher(
                    ansible_config)) or is_upgrade_from_aap23_hub46():
                continue

            expected_name = f"collection_dep_a_{expected_col['name']}"
            actual_col = collection_info(gc, expected_col["repository"],
                                         expected_col["namespace"], expected_name,
                                         expected_col["version"])
            assert actual_col["version"] == expected_col["version"]
            assert actual_col["name"] == expected_name
            assert actual_col["namespace"]["name"] == expected_col["namespace"]
            if not galaxy_auto_sign_collections():
                if expected_col["signed"]:
                    assert len(actual_col["signatures"]) > 0
                else:
                    assert len(actual_col["signatures"]) == 0
            else:
                assert len(actual_col["signatures"]) > 0
            if is_hub_4_7_or_higher(ansible_config):
                _, actual_col = search_collection_endpoint(gc, name=expected_name)
                assert actual_col[0]["is_deprecated"] == expected_col["deprecated"]
                if galaxy_auto_sign_collections():
                    assert actual_col[0]["is_signed"] is True
                else:
                    assert actual_col[0]["is_signed"] == expected_col["signed"]
                assert actual_col[0]["cv_name"] == expected_name
                assert actual_col[0]["cv_version"] == expected_col["version"]
                assert actual_col[0]["repo_name"] == expected_col["repository"]

    @pytest.mark.min_hub_version("4.6dev")
    @pytest.mark.verify_data
    def test_verify_data_groups(self, galaxy_client, data):
        """
        Test that verifies the data previously loaded by test_load_data
        """
        gc = galaxy_client("admin")
        for expected_group in data["groups"]:
            get_group_id(gc, expected_group["name"])

    @pytest.mark.min_hub_version("4.7dev")
    @pytest.mark.skipif(is_upgrade_from_aap23_hub46(), reason=SKIP_MESSAGE)
    @pytest.mark.verify_data
    def test_verify_data_repos(self, galaxy_client, data):
        """
        Test that verifies the data previously loaded by test_load_data
        """
        gc = galaxy_client("admin")
        for expected_repo in data["repositories"]:
            get_repository_href(gc, expected_repo["name"])

    @pytest.mark.min_hub_version("4.6dev")
    @pytest.mark.verify_data
    def test_verify_data_rbac_roles(self, galaxy_client, data):
        """
        Test that verifies the data previously loaded by test_load_data
        """
        gc = galaxy_client("admin")
        for expected_rbac_role in data["roles"]:
            role_info_1 = get_role(gc, expected_rbac_role["name"])
            assert role_info_1["name"] == expected_rbac_role["name"]
            assert role_info_1["description"] == expected_rbac_role["description"]
            assert sorted(role_info_1["permissions"]) == sorted(
                expected_rbac_role["permissions"])

    @pytest.mark.min_hub_version("4.7dev")
    @pytest.mark.verify_data
    def test_verify_data_ee(self, galaxy_client, data):
        """
        Test that verifies the data previously loaded by test_load_data
        """
        gc = galaxy_client("admin")
        for ee in data["execution_environments"]:
            # this needs to be moved to galaxykit
            actual_ee = gc.get(f"v3/plugin/execution-environments/repositories/{ee['name']}/")
            assert actual_ee["name"] == ee["name"]
            assert (actual_ee["pulp"]["repository"]["remote"]["upstream_name"]
                    == ee["upstream_name"])
            actual_registry = actual_ee["pulp"]["repository"]["remote"]["registry"]
            expected_registry = get_registry_pk(gc, ee["remote_registry"])
            assert expected_registry == actual_registry

    @pytest.mark.min_hub_version("4.6dev")
    @pytest.mark.verify_data
    def test_verify_data_remote_registries(self, galaxy_client, data):
        """
        Test that verifies the data previously loaded by test_load_data
        """
        gc = galaxy_client("admin")
        for remote_registry in data["remote_registries"]:
            # this needs to be moved to galaxykit
            actual_rr = gc.get(f"_ui/v1/execution-environments/registries/"
                               f"?name={remote_registry['name']}")
            assert actual_rr["data"][0]["name"] == remote_registry["name"]
            assert actual_rr["data"][0]["url"] == remote_registry["url"]

    @pytest.mark.min_hub_version("4.6dev")
    @pytest.mark.verify_data
    def test_verify_data_remotes(self, galaxy_client, data):
        """
        Test that verifies the data previously loaded by test_load_data
        """
        gc = galaxy_client("admin")
        for remote in data["remotes"]:
            actual_remote = view_remotes(gc, remote["name"])
            assert actual_remote["results"][0]["url"] == remote["url"]
            assert actual_remote["results"][0]["name"] == remote["name"]
            assert actual_remote["results"][0]["signed_only"] == remote["signed_only"]
            assert actual_remote["results"][0]["tls_validation"] == remote["tls_validation"]
