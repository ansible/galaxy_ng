"""
load data
"""
import pytest
import yaml

from galaxy_ng.tests.integration.conftest import ansible_config
from galaxy_ng.tests.integration.utils import get_client, set_certification
from galaxy_ng.tests.integration.utils.repo_management_utils import create_repo_and_dist, \
    upload_new_artifact, add_content_units
from galaxykit.collections import sign_collection
from galaxykit.containers import create_container
from galaxykit.namespaces import add_group
from galaxykit.registries import create_registry
from galaxykit.remotes import create_remote
from galaxykit.repositories import get_repository_href
from galaxykit.utils import wait_for_task


@pytest.mark.min_hub_version("4.6dev")
class TestLoadData:

    @pytest.mark.load_data
    def test_load_data(self, galaxy_client, ansible_config):
        """
        Verifies that
        """

        config = ansible_config("partner_engineer")
        api_client = get_client(config, request_token=True, require_auth=True)
        gc = galaxy_client("admin")
        api_client.config["upload_signatures"] = True
        # resp = upload_artifact(config, api_client, artifact)
        # wait_for_task(api_client, resp)

        path = 'galaxy_ng/tests/integration/load_data.yaml'

        with open(path, 'r') as yaml_file:
            data = yaml.safe_load(yaml_file)

        for group in data["groups"]:
            gc.create_group(group["name"])

        for user in data["users"]:
            gc.get_or_create_user(user["username"], user["password"], group=None)
            if user["group"]:
                group = gc.get_group(user["group"])
                gc.add_user_to_group(user["username"], group["id"])

        for ns in data["namespaces"]:
            gc.create_namespace(ns["name"], ns["group"], object_roles=["galaxy.collection_namespace_owner"])
            add_group(gc, ns["name"], ns["group"], object_roles=["galaxy.collection_namespace_owner"])

        for repo in data["repositories"]:
            try:
                create_repo_and_dist(gc, repo["name"])
            except Exception as e:
                print(e)

        for remote in data["remotes"]:
            try:
                create_remote(gc, remote["name"], gc.galaxy_root)
            except Exception as e:
                print(e)

        for collection in data["collections"]:
            try:
                artifact = upload_new_artifact(gc, collection["namespace"], collection["repository"], collection["version"], collection["name"])
                collection_resp_1 = gc.get(
                    f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
                )
                repo_pulp_href = get_repository_href(gc, collection["repository"])
                content_units = [
                    collection_resp_1["results"][0]["pulp_href"],
                 ]
                add_content_units(gc, content_units, repo_pulp_href)
                if collection["signed"]:
                    sign_collection(gc, collection_resp_1["results"][0]["pulp_href"], repo_pulp_href)
            except Exception:
                pass

        for role in data["roles"]:
            name = role["name"]
            description = role["description"]
            permissions = role["permissions"]
            try:
                gc.create_role(name, description, permissions)
            except Exception as e:
                pass

        for remote in data["remotes"]:
            try:
                create_remote(gc, remote["name"], remote["url"],
                              remote["signed_only"], remote["tls_validation"])
            except Exception:
                pass

        for remote_registry in data["remote_registries"]:
            try:
                create_registry(gc, remote_registry["name"], remote_registry["url"])
            except Exception:
                pass

        for ee in data["execution_environments"]:
            create_container(gc, ee["name"], ee["upstream_name"], ee["remote_registry"])




