"""test_sync_enhancement_endpoints.py - Tests related to sync enhancements.
"""
from ..utils import get_client, wait_for_task, set_certification


def test_pulp_repo_metadata_endpoint(ansible_config):
    """Tests whether the landing page returns the expected fields and numbers."""

    client = get_client(config=ansible_config("basic_user"), request_token=True, require_auth=True)
    api_prefix = client.config.get("api_prefix").rstrip("/")

    result = client(f"{api_prefix}/v3/")
    assert "published" in result


def test_pulp_all_collections_endpoint(ansible_config, artifact, upload_artifact):
    """Tests the unpaginated endpoint that returns all collections,
    checks the expected artifact is present."""

    config = ansible_config("partner_engineer")
    api_client = get_client(config, request_token=True, require_auth=True)
    api_prefix = api_client.config.get("api_prefix").rstrip("/")

    resp = upload_artifact(config, api_client, artifact)
    wait_for_task(api_client, resp)

    set_certification(api_client, artifact)
    artifact_href = (
        f"{api_prefix}/v3/plugin/ansible/content/published/collections/index/"
        f"{artifact.namespace}/{artifact.name}/versions/{artifact.version}/"
    )

    # check artifact is listed in unpaginated endpoint with all collections
    all_collections = api_client(
        f"{api_prefix}/v3/plugin/ansible/content/published/collections/all-collections/",
        method="GET",
    )
    assert artifact_href in [
        collection["highest_version"]["href"] for collection in all_collections
    ]

    # check using alternative url format, which uses default distro
    all_collections = api_client(f"{api_prefix}/v3/collections/all/", method="GET")
    assert artifact_href in [
        collection["highest_version"]["href"] for collection in all_collections
    ]

    # check using another alternative url format
    all_collections = api_client(
        f"{api_prefix}/content/published/v3/collections/all/", method="GET"
    )
    artifact_href = (
        f"{api_prefix}/content/published/v3/plugin/ansible/content/published/collections/index/"
        f"{artifact.namespace}/{artifact.name}/versions/{artifact.version}/"
    )
    assert artifact_href in [
        collection["highest_version"]["href"] for collection in all_collections
    ]


def test_pulp_all_versions_endpoint(ansible_config, artifact, upload_artifact):
    """Tests the unpaginated endpoint that returns all collection versions,
    checks the expected artifact is present."""

    config = ansible_config("partner_engineer")
    api_client = get_client(config, request_token=True, require_auth=True)
    api_prefix = api_client.config.get("api_prefix").rstrip("/")

    resp = upload_artifact(config, api_client, artifact)
    wait_for_task(api_client, resp)

    set_certification(api_client, artifact)
    artifact_href = (
        f"{api_prefix}/v3/plugin/ansible/content/published/collections/index/"
        f"{artifact.namespace}/{artifact.name}/versions/{artifact.version}/"
    )

    # check artifact is listed in unpaginated endpoint with all collection versions
    all_versions = api_client(
        f"{api_prefix}/v3/plugin/ansible/content/published/collections/all-versions/",
        method="GET",
    )
    assert artifact_href in [version["href"] for version in all_versions]

    # check using alternative url format, which uses default distro
    all_versions = api_client(f"{api_prefix}/v3/collection_versions/all/", method="GET")
    assert artifact_href in [version["href"] for version in all_versions]
