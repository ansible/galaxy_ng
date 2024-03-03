import pytest

from galaxykit.repositories import search_collection
from ..utils.iqe_utils import require_signature_for_approval
from ..utils import get_client, SocialGithubClient


@pytest.mark.min_hub_version("4.7dev")
@pytest.mark.all
@pytest.mark.skipif(require_signature_for_approval(),
                    reason="This test needs refactoring to work with signatures"
                           " required on move.")
def test_x_repo_search_acl_basic_user(uncertifiedv2, galaxy_client):
    """Check if admin and basic user can perform x-repo searches"""
    # GALAXY_SIGNATURE_UPLOAD_ENABLED="false" in ephemeral env
    gc_admin = galaxy_client("admin")

    # Enumerate published collection info ...
    ckeys = []
    for cv in uncertifiedv2:
        ckeys.append((cv.namespace, cv.name, cv.version))

    # /api/automation-hub/v3/plugin/ansible/search/collection-versions/
    namespace = ckeys[0][0]
    name = ckeys[0][1]
    resp = search_collection(gc_admin, namespace=namespace, name=name)
    assert resp['meta']['count'] == 2

    gc_basic = galaxy_client("basic_user")
    resp = search_collection(gc_basic, namespace=namespace, name=name)
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
        + f'?namespace={namespace}&name={name}&repository_name=published'
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
        + f'?namespace={namespace}&name={name}&repository_name=published'
    )
    resp = api_client.request(search_url)
    assert resp['meta']['count'] == 2

    search_url = (
        'v3/plugin/ansible/search/collection-versions/'
        + f'?namespace={namespace}&name={name}&repository_name=published'
    )
    cfg = ansible_config('github_user_1')
    with SocialGithubClient(config=cfg) as client:
        resp = client.get(search_url)
