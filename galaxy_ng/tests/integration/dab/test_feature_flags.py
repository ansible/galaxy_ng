import os
import pytest


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10")
@pytest.mark.skipif(
    os.getenv("ENABLE_DAB_TESTS"),
    reason="Skipping test because ENABLE_DAB_TESTS is set"
)
def test_feature_flags_endpoint_is_exposed(galaxy_client):
    """
    We want the download url to point at the gateway
    """
    gc = galaxy_client("admin")
    flag_url = "feature_flags_state/"
    resp = gc.get(flag_url, parse_json=False)
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == 'application/json'
