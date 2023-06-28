import pytest
from ..utils import get_client, SocialGithubClient


@pytest.mark.min_hub_version("4.7dev")
@pytest.mark.all
def test_x_repo_search_acl_basic_user(ansible_config, uncertifiedv2, settings):
    """Check if admin and basic user can perform x-repo searches"""
    if settings.get("GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL"):
        pytest.skip("This test needs refactoring to work with signatures required on move.")

    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    # Enumerate published collection info ...
    ckeys = []
    for cv in uncertifiedv2:
        ckeys.append((cv.namespace, cv.name, cv.version))

    # /api/automation-hub/v3/plugin/ansible/search/collection-versions/
    namespace = ckeys[0][0]
    name = ckeys[0][1]
    search_url = (
        api_prefix
        + '/v3/plugin/ansible/search/collection-versions/'
        + f'?namespace={namespace}&name={name}'
    )
    resp = api_client.request(search_url)
    assert resp['meta']['count'] == 2

    config = ansible_config("basic_user")
    basic_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )
    resp = basic_client.request(search_url)
    assert resp['meta']['count'] == 2


@pytest.mark.deployment_community
@pytest.mark.min_hub_version("4.7dev")
def test_x_repo_search_acl_anonymous_user(ansible_config, auto_approved_artifacts):
    """Check if anonymous users can perform x-repo searches"""

    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    # Enumerate published collection info ...
    ckeys = []
    for cv in auto_approved_artifacts:
        ckeys.append((cv.namespace, cv.name, cv.version))

    # /api/automation-hub/v3/plugin/ansible/search/collection-versions/
    namespace = ckeys[0][0]
    name = ckeys[0][1]
    search_url = (
        api_prefix
        + '/v3/plugin/ansible/search/collection-versions/'
        + f'?namespace={namespace}&name={name}'
    )
    resp = api_client.request(search_url)
    assert resp['meta']['count'] == 2

    config = ansible_config("anonymous_user")
    anonymous_client = get_client(
        config=config,
        request_token=False,
        require_auth=False
    )
    resp = anonymous_client.request(search_url)
    assert resp['meta']['count'] == 2


@pytest.mark.deployment_community
@pytest.mark.min_hub_version("4.7dev")
def test_x_repo_search_acl_social_user(ansible_config, auto_approved_artifacts):
    """Check if a social user can perform x-repo searches"""

    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    # Enumerate published collection info ...
    ckeys = []
    for cv in auto_approved_artifacts:
        ckeys.append((cv.namespace, cv.name, cv.version))

    # /api/automation-hub/v3/plugin/ansible/search/collection-versions/
    namespace = ckeys[0][0]
    name = ckeys[0][1]
    search_url = (
        api_prefix
        + '/v3/plugin/ansible/search/collection-versions/'
        + f'?namespace={namespace}&name={name}'
    )
    resp = api_client.request(search_url)
    assert resp['meta']['count'] == 2

    search_url = (
        'v3/plugin/ansible/search/collection-versions/'
        + f'?namespace={namespace}&name={name}'
    )
    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get(search_url)
