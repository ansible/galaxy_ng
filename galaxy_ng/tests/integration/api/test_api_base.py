from ..utils import get_client


def test_galaxy_api_root(ansible_config, artifact):
    """Test galaxy API root."""

    config = ansible_config("ansible_partner")

    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    # verify api root works
    response = api_client('/api/automation-hub/')
    assert "v3" in response["available_versions"]
    assert "pulp-v3" in response["available_versions"]
