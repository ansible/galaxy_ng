import os

import pytest
import requests


@pytest.mark.all
@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer invalid"}],
    ids=["anonymous", "invalid-authorization"],
)
def test_readiness_status_endpoint_is_public_and_compact(headers):
    api_root = os.environ.get("HUB_API_ROOT", "http://localhost:5001/api/galaxy/")
    response = requests.get(
        f"{api_root.rstrip('/')}/status/",
        headers={"Accept": "application/json", **headers},
        timeout=30,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "good", "issues": []}
