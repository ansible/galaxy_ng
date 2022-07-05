import pytest
from ansible.galaxy.api import GalaxyError

from ..utils import get_client


@pytest.mark.standalone_only
@pytest.mark.pulp_api
def test_pulp_api_redirect(ansible_config, artifact):
    """Test that /pulp/ is redirecting to /api/galaxy/pulp/"""

    config = ansible_config("admin")

    api_client = get_client(config=config, request_token=True, require_auth=True)

    # verify api root works
    response = api_client("/pulp/api/v3/")
    assert "users" in response

    # verify a couple of different paths work
    response = api_client("/pulp/api/v3/status/")
    assert "versions" in response

    response = api_client("/pulp/api/v3/distributions/ansible/ansible/")
    assert response["count"] > 0

    # verify query params work
    response = api_client("/pulp/api/v3/distributions/ansible/ansible/?name=published")
    assert response["count"] == 1

    # verify the hrefs are not returning the old url
    assert not response["results"][0]["pulp_href"].startswith("/pulp/")


@pytest.mark.parametrize(
    "url",
    [
        "/api/automation-hub/pulp/api/v3/repositories/ansible/ansible/",
    ],
)
@pytest.mark.pulp_api
def test_pulp_endpoint_readonly(ansible_config, artifact, url):
    """Ensure authenticated user has readonly access to view"""

    config = ansible_config("admin")
    api_client = get_client(config, request_token=True, require_auth=True)

    REGEX_40X = r"HTTP Code: 40\d"

    # NOTE: with `count` this only applies to lists, can be adjusted for future views
    response = api_client(url, method="GET")
    assert "count" in response

    with pytest.raises(GalaxyError, match=REGEX_40X):
        api_client(url, method="POST")

    with pytest.raises(GalaxyError, match=REGEX_40X):
        api_client(url, method="PUT")

    with pytest.raises(GalaxyError, match=REGEX_40X):
        api_client(url, method="DELETE")
