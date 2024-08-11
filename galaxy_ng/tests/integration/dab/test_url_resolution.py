import os
import pytest
import requests


@pytest.mark.deployment_standalone
@pytest.mark.skipif(
    not os.getenv("JWT_PROXY"),
    reason="Skipping test because it only works with JWT_PROXY."
)
def test_dab_collection_download_url_hostnames(settings, galaxy_client, published):
    """
    We want the download url to point at the gateway
    """
    gc = galaxy_client("admin")
    cv_url = 'v3/plugin/ansible/content/published/collections/index/'
    cv_url += f'{published.namespace}/{published.name}/versions/{published.version}/'
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

    # now check if we access it from localhost that the download url changes accordingly
    if gc.galaxy_root == "http://jwtproxy:8080/api/galaxy/":
        local_url = os.path.join(gc.galaxy_root, cv_url)
        local_url = local_url.replace("http://jwtproxy:8080", "http://localhost:5001")
        cv_info = gc.get(local_url, auth=("admin", "admin"))

        download_url = cv_info["download_url"]
        assert download_url.startswith("http://localhost:5001")

        # try to GET the tarball ...
        dl_resp = gc.get(download_url, parse_json=False, auth=("admin", "admin"))
        assert dl_resp.status_code == 200
        assert dl_resp.headers.get('Content-Type') == 'application/gzip'
        assert dl_resp.url.startswith("http://localhost:5001")


@pytest.mark.deployment_standalone
@pytest.mark.skipif(
    not os.getenv("JWT_PROXY"),
    reason="Skipping test because it only works with JWT_PROXY."
)
def test_dab_token_server_hostnames(settings, galaxy_client):
    """
    The www-authenticate header from /v2/ should preserve the original hostname
    """
    v2_hosts = [
        'jwtproxy:8080',
        'localhost:5001',
    ]

    for v2_host in v2_hosts:
        rr = requests.get('http://' + v2_host + '/v2/')
        headers = {}
        for k, v in dict(rr.headers).items():
            headers[k.lower()] = v

        # Bearer realm="http://jwtproxy:8080/token/",service="jwtproxy:8080"
        auth = headers['www-authenticate']
        auth_parts = auth.split(',')
        bearer_realm = auth_parts[0].split('"')[1]
        service = auth_parts[1].split('"')[1]

        assert bearer_realm == 'http://' + v2_host + '/token/'
        assert service == v2_host
