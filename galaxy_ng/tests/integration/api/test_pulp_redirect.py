import pytest

from ..utils import get_client


@pytest.mark.standalone_only
def test_pulp_api_redirect(ansible_config, artifact):
    """Test that /pulp/ is redirecting to /api/galaxy/pulp/"""

    config = ansible_config("ansible_partner")

    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    # verify api root works
    response = api_client('/pulp/api/v3/')
    assert "users" in response

    # verify a couple of different paths work
    response = api_client('/pulp/api/v3/status/')
    assert "versions" in response

    response = api_client('/pulp/api/v3/distributions/ansible/ansible/')
    assert response["count"] > 0

    # verify query params work
    response = api_client('/pulp/api/v3/distributions/ansible/ansible/?name=published')
    assert response["count"] == 1

    # verify the hrefs are not returning the old url
    assert not response["results"][0]["pulp_href"].startswith("/pulp/")
