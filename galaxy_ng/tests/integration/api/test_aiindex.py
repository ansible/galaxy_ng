import pytest

from ..utils import (
    UIClient,
    SocialGithubClient,
    create_unused_namespace,
    generate_unused_namespace,
    get_client
)

# should we import this like this
# or move that function to utils?
from .test_community import cleanup_social_user


@pytest.fixture(scope="function")
def flags(ansible_config):
    config = ansible_config("admin")
    api_client = get_client(config, request_token=True, require_auth=True)
    api_prefix = api_client.config.get("api_prefix").rstrip("/")
    return api_client(f"{api_prefix}/_ui/v1/feature-flags/")


@pytest.fixture(scope="function")
def namespace(ansible_config) -> str:
    """create a new namespace."""
    config = ansible_config("admin")
    api_client = get_client(config, request_token=True, require_auth=True)
    return create_unused_namespace(api_client)


@pytest.fixture(scope="function")
def pe_namespace(ansible_config) -> str:
    """create a new namespace owned by PE user."""
    config = ansible_config("partner_engineer")
    api_client = get_client(config, request_token=True, require_auth=True)
    new_namespace = generate_unused_namespace(api_client=api_client, api_version="_ui/v1")
    with UIClient(config=config) as uclient:
        # get user
        resp = uclient.get("_ui/v1/me/")
        ds = resp.json()
        # create ns with group
        payload = {
            "name": new_namespace,
            "groups": [
                {
                    "id": ds["groups"][0]["id"],
                    "name": ds["groups"][0]["name"],
                    "object_roles": ["galaxy.collection_admin"],
                }
            ],
        }
        presp = uclient.post("_ui/v1/my-namespaces/", payload=payload)
        assert presp.status_code == 201
    return new_namespace


@pytest.fixture(scope="function")
def legacy_namespace(ansible_config):
    """Creates a new legacy namespace owned by gh01 user"""

    cleanup_social_user('gh01', ansible_config)

    cfg = ansible_config("github_user_1")
    with SocialGithubClient(config=cfg) as client:
        resp = client.get('v1/namespaces/?name=gh01')
        result = resp.json()
        assert result['count'] == 1
        assert result['results'][0]['name'] == 'gh01'

        # the user should have been added as an owner on the namespace
        assert result['results'][0]['summary_fields']['owners'][0]['username'] == 'gh01'

    return 'gh01'


@pytest.mark.deployment_community
def test_legacy_namespace_add_list_remove_aiindex(ansible_config, legacy_namespace, flags):
    """Test the whole workflow for AIindex.

    1. Create a new legacy_namespace (by fixture)
    2. Add legacy_namespace to AIIndex
    3. Assert legacy_namespace is listed  on _ui/v1/ai_deny_index/
    4. Assert ai_deny_index filters works for scope and name
    5. Remove legacy_namespace from AIIndex
    6. Assert legacy_namespace is not listed on _ui/v1/ai_deny_index/
    7. Repeat step 2 with github_user_2
    8. Assert permission error raises
    """
    if not flags.get("ai_deny_index"):
        pytest.skip("ai_deny_index flag is not enabled")

    cfg = ansible_config("github_user_1")
    with SocialGithubClient(config=cfg) as client:
        assert (
            client.post(
                "_ui/v1/ai_deny_index/legacy_namespace/",
                data={"reference": legacy_namespace}
            ).status_code == 201
        )

        # 3. Assert legacy_namespace is listed  on _ui/v1/ai_deny_index/
        response = client.get("_ui/v1/ai_deny_index/")
        assert response.status_code == 200
        expected = {"scope": "legacy_namespace", "reference": legacy_namespace}
        assert expected in response.json()["results"]

        # 4. Assert ai_deny_index filters works for scope and name
        assert (
            client.get(
                f"_ui/v1/ai_deny_index/?scope=legacy_namespace&reference={legacy_namespace}"
            ).json()["results"][0]["reference"] == legacy_namespace
        )

        # 5. Remove legacy_namespace from AIIndex
        assert (
            client.delete(
                f"_ui/v1/ai_deny_index/legacy_namespace/{legacy_namespace}/"
            ).status_code == 204
        )

        # 6. Assert legacy_namespace is not listed on _ui/v1/ai_deny_index/
        response = client.get("_ui/v1/ai_deny_index/")
        assert response.status_code == 200
        expected = {"scope": "legacy_namespace", "reference": legacy_namespace}
        assert expected not in response.json()["results"]

    cfg = ansible_config("github_user_2")
    with SocialGithubClient(config=cfg) as client:
        # 7. Repeat step 2 with github_user_2
        assert (
            client.post(
                "_ui/v1/ai_deny_index/legacy_namespace/",
                data={"reference": legacy_namespace}
            ).status_code == 403
        )


@pytest.mark.deployment_community
def test_namespace_add_list_remove_aiindex(ansible_config, namespace, pe_namespace, flags):
    """Test the whole workflow for AIindex.

    1. Create a new namespace (by fixture)
    2. Add namespace to AIIndex
    3. Assert namespace is listed  on _ui/v1/ai_deny_index/
    4. Assert ai_deny_index filters works for scope and name
    5. Remove namespace from AIIndex
    6. Assert namespace is not listed on _ui/v1/ai_deny_index/
    7. Repeat step 2 with a basic user
    8. Assert permission error raises
    """
    if not flags.get("ai_deny_index"):
        pytest.skip("ai_deny_index flag is not enabled")

    with UIClient(config=ansible_config("admin")) as client:
        # 2. Add namespace to AIIndex
        assert (
            client.post(
                "_ui/v1/ai_deny_index/namespace/",
                payload={"reference": namespace}
            ).status_code == 201
        )

        # 3. Assert namespace is listed  on _ui/v1/ai_deny_index/
        response = client.get("_ui/v1/ai_deny_index/")
        assert response.status_code == 200
        expected = {"scope": "namespace", "reference": namespace}
        assert expected in response.json()["results"]

        # 4. Assert ai_deny_index filters works for scope and name
        assert (
            client.get(
                f"_ui/v1/ai_deny_index/?scope=namespace&reference={namespace}"
            ).json()["count"] == 1
        )
        assert client.get(
            f"_ui/v1/ai_deny_index/?reference={namespace}"
        ).json()["count"] == 1
        assert (
            client.get(
                "_ui/v1/ai_deny_index/?scope=legacy_namespace&reference=xyz_123"
            ).json()["count"]
            == 0
        )

        # 5. Remove namespace from AIIndex
        response = client.delete(f"_ui/v1/ai_deny_index/namespace/{namespace}")
        assert response.status_code == 204

        # 6. Assert namespace is not listed on _ui/v1/ai_deny_index/
        response = client.get("_ui/v1/ai_deny_index/")
        assert response.status_code == 200
        expected = {"scope": "namespace", "reference": namespace}
        assert expected not in response.json()["results"]

    # 7. Repeat step 2 with a basic user
    with UIClient(config=ansible_config("basic_user")) as uclient:
        # 8. Assert permission error raises
        assert (
            uclient.post(
                "_ui/v1/ai_deny_index/namespace/",
                payload={"reference": namespace}
            ).status_code == 403
        )

    with UIClient(config=ansible_config("partner_engineer")) as uclient:
        # 9. add to the AI Index, a namespace owned by PE
        assert (
            uclient.post(
                "_ui/v1/ai_deny_index/namespace/",
                payload={"reference": pe_namespace}
            ).status_code == 201
        )

        # 11. Assert the namespace is listed on _ui/v1/ai_deny_index/
        response = uclient.get("_ui/v1/ai_deny_index/")
        assert response.status_code == 200
        expected = {"scope": "namespace", "reference": pe_namespace}
        assert expected in response.json()["results"]

        # 5. Remove namespace from AIIndex
        response = uclient.delete(f"_ui/v1/ai_deny_index/namespace/{pe_namespace}")
        assert response.status_code == 204
