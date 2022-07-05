"""test_landing_page.py - Test related to landing page endpoint.
"""
import pytest
from ansible.galaxy.api import GalaxyError

from ..utils import get_client


def test_pulp_sync_enhancement_endpoints(ansible_config):
    """Tests whether the landing page returns the expected fields and numbers."""

    client = get_client(config=ansible_config("admin"), request_token=True, require_auth=True)

    # verify that the repo metadate endpoint works
    results = client("/api/automation-hub/v3/")
    assert "published" in results

    # verify that the unpaginated endpoints are disabled
    with pytest.raises(GalaxyError) as ctx:
        client("/api/automation-hub/v3/collections/all/", method="GET")
    assert ctx.value.http_code == 404

    with pytest.raises(GalaxyError) as ctx:
        client("/api/automation-hub/v3/collection_versions/all/", method="GET")
    assert ctx.value.http_code == 404

    # verify that the content/ prefix works correctly unpaginated endpoints are disabled
    with pytest.raises(GalaxyError) as ctx:
        client("/api/automation-hub/content/published/v3/collections/all/", method="GET")
    assert ctx.value.http_code == 404

    with pytest.raises(GalaxyError) as ctx:
        client("/api/automation-hub/content/published/v3/collection_versions/all/", method="GET")
    assert ctx.value.http_code == 404
