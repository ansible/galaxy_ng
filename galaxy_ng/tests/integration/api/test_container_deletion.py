import subprocess
from urllib.parse import urlparse
from galaxy_ng.tests.integration.utils import get_client, UIClient

def test_container_content_deletion(ansible_config):
    cfg = ansible_config("admin")
    api_prefix = cfg.get("api_prefix").rstrip("/")

    api_client = get_client(cfg, request_token=True, require_auth=True)

    # Create registry remote
    payload = {'name': 'quay', 'url': 'https://quay.io'}
    registry_response = api_client(f'{api_prefix}/v3/remotes/', args=payload, method='POST')
    assert registry_response.status_code == 200

    # create repo "alpine"
