import time
import pytest

from galaxy_ng.tests.performance.constants import URLS
from ..integration.utils import (
    UIClient,
    get_client,
)


@pytest.fixture
def api_client(ansible_config):
    config = ansible_config("admin")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=False
    )
    return api_client


@pytest.mark.deployment_community
@pytest.mark.parametrize(("url", "info"), URLS.items())
def test_api_performance(ansible_config, api_client, url, info):
    threshold = 0.25
    results = []
    cfg = ansible_config('basic_user')
    with UIClient(config=cfg) as uclient:
        start_time = time.time()
        uclient.get(url)
        elapsed_time = time.time() - start_time
        difference = (elapsed_time - info['baseline']) / info['baseline']
        results.append({url: difference})
        assert difference < threshold
