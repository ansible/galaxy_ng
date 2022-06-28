from ..utils import get_client


def test_galaxy_api_root(ansible_config, artifact):
    """Test galaxy API root."""

    # TODO: change to `basic_user` profile when can access pulp-v3 api root
    config = ansible_config("admin")

    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    # verify api root works
    response = api_client('/api/automation-hub/')
    assert "v3" in response["available_versions"]
    assert "pulp-v3" in response["available_versions"]

    v3_root = api_client('/api/automation-hub/' + response['available_versions']['v3'])
    assert "published" in v3_root

    pulp_root = api_client('/api/automation-hub/' + response['available_versions']['pulp-v3'])
    assert "tasks" in pulp_root
