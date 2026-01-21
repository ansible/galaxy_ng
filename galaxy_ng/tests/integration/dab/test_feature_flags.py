import os
import pytest
from packaging.version import parse as parse_version

from ..utils.iqe_utils import get_hub_version


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10")
@pytest.mark.skipif(
    os.getenv("ENABLE_DAB_TESTS"),
    reason="Skipping test because ENABLE_DAB_TESTS is set"
)
def test_feature_flags_endpoint_is_exposed(galaxy_client, ansible_config):
    """
    We want the download url to point at the gateway.

    Note: The feature flags endpoint URL changed between AAP 2.5 and 2.6:
    - AAP 2.5 (Hub 4.10): feature_flags_state/
    - AAP 2.6+ (Hub 4.11+): feature_flags/states/
    """
    gc = galaxy_client("admin")

    # Determine the correct URL based on Hub version
    hub_version = get_hub_version(ansible_config)
    if parse_version(hub_version) < parse_version("4.11"):
        # AAP 2.5 uses the old URL format
        flag_url = "feature_flags_state/"
    else:
        # AAP 2.6+ uses the new platform flags URL
        flag_url = "feature_flags/states/"

    resp = gc.get(flag_url, parse_json=False)
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == 'application/json'
