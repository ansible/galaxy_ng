import pytest
from ..utils import UIClient


@pytest.mark.standalone_only
@pytest.mark.api_ui
def test_api_ui_v1_collection_versions_version_range(ansible_config, uncertifiedv2):
    """Test the ?version_range query parameter."""
    c1, c2 = uncertifiedv2
    cfg = ansible_config('basic_user')
    v_path = f"_ui/v1/collection-versions/?name={c1.name}&namespace={c1.namespace}"

    with UIClient(config=cfg) as uclient:
        # test single version
        resp = uclient.get(f'{v_path}&version_range=={c1.version}')
        ds = resp.json()

        assert len(ds['data']) == 1
        assert ds['data'][0]["version"] == c1.version

        # test range
        resp = uclient.get(f'{v_path}&version_range=>={c1.version}')
        ds = resp.json()

        assert len(ds['data']) == 2
        assert set([v["version"] for v in ds['data']]) == set([c1.version, c2.version])

        # test range exclusive
        resp = uclient.get(f'{v_path}&version_range=>{c1.version}')
        ds = resp.json()

        assert len(ds['data']) == 1
        assert ds['data'][0]["version"] == c2.version

        # test invalid
        resp = uclient.get(f'{v_path}&version_range=not_a_semver_version')
        assert resp.status_code == 400
