"""test_landing_page.py - Test related to landing page endpoint.
"""
import pytest
from galaxykit.utils import GalaxyClientError


def test_pulp_sync_enhancement_endpoints(galaxy_client):
    """Tests whether the landing page returns the expected fields and numbers."""
    gc = galaxy_client("admin")
    v3_root = gc.get("v3/plugin/ansible/content/published/collections/")
    assert "published" in v3_root

    # verify that the unpaginated endpoints are disabled
    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("v3/collections/all/", parse_json=False)
    assert ctx.value.response.status_code == 404

    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("v3/collection_versions/all/", parse_json=False)
    assert ctx.value.response.status_code == 404

    # verify that the content/ prefix works correctly unpaginated endpoints are disabled
    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("content/published/v3/collections/all/", parse_json=False)
    assert ctx.value.response.status_code == 404

    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("content/published/v3/collection_versions/all/", parse_json=False)
    assert ctx.value.response.status_code == 404
