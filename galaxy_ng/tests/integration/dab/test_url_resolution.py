import os
import pytest


@pytest.mark.skipif(not os.getenv("ENABLE_DAB_TESTS"), reason="Skipping test because ENABLE_DAB_TESTS is not set")
def test_dab_collection_download_url_hostnames(settings, galaxy_client, published):
    """
    We want the download url to point at the gateway
    """
    gc = galaxy_client("admin")
    cv_url = f'v3/plugin/ansible/content/published/collections/index/{published.namespace}/{published.name}/versions/{published.version}'
    cv_info = gc.get(cv_url)
    download_url = cv_info['download_url']
    assert download_url.startswith(gc.galaxy_root)

    # try to GET the tarball ...
    dl_resp = gc.get(download_url, parse_json=False)
    assert dl_resp.status_code == 200
    assert dl_resp.headers.get('Content-Type') == 'application/gzip'

    # make sure the final redirect was through the gateway ...
    expected_url = gc.galaxy_root.replace('/api/galaxy/', '')
    assert dl_resp.url.startswith(expected_url)
