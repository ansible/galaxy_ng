import pytest
import logging

from galaxy_ng.tests.integration.utils.rbac_utils import upload_test_artifact

from galaxy_ng.tests.integration.utils.repo_management_utils import create_repo_and_dist, \
    create_test_namespace, upload_new_artifact
from galaxy_ng.tests.integration.utils.tools import generate_random_string
from galaxykit.utils import GalaxyClientError

logger = logging.getLogger(__name__)


@pytest.mark.min_hub_version("4.7dev")
class TestRepositories:

    @pytest.mark.repositories
    @pytest.mark.standalone_only
    def test_cant_upload_same_collection_same_repo(self, galaxy_client):
        """
        Verifies that the same collection / version cannot be uploaded to the same repo
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(gc, namespace_name, test_repo_name, "0.0.1")
        with pytest.raises(GalaxyClientError) as ctx:
            upload_test_artifact(gc, namespace_name, test_repo_name, artifact)
        assert ctx.value.response.status_code == 400
