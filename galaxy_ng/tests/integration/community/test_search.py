"""
Test Community Search

Setup:

    1. Create a namespace
    2. Upload a collection
    3. Create a legacy namespace
    4. Import a role

For each search_type=[websearch, sql]:

    1. Search with no parameters
    2. Search with name facet
    3. Search with namespace facet
    4. Search with deprecated facet
    5. Search with type facet
    6. Search with platform facet
    7. Search with tags
    8. Search with keywords
        - simple
        - compound
        - conditional
    9. Test order-by asc,desc
"""

import pytest
from orionutils.generator import build_collection

from ..utils import ansible_galaxy, get_client, upload_artifact, wait_for_task

NAMESPACE_NAME = "ansible"
COLLECTION_NAME = "galaxy_fake_collection"
COLLECTION_TAGS = ["database", "api", "galaxy"]
COLLECTION_DESCRIPTION = "collection to pretend to manage galaxy with infinidash support on fedora"
ROLE_NAME = "ansible-kubernetes-modules"
ROLE_DESCRIPTION = "Pre-release Kubernetes modules"
ROLE_TAGS = ["k8s", "kubernetes", "openshift", "modules", "api"]
GITHUB_USER = "ansible"
GITHUB_REPO = "ansible-kubernetes-modules"
BRANCH = "v0.0.1"


@pytest.fixture(autouse=True, scope="module")
def my_setup_module(ansible_config):
    """Arrange"""
    admin_config = ansible_config("admin")
    admin_client = get_client(config=admin_config, request_token=False, require_auth=True)
    # Create a collection namespace
    collection_ns = admin_client(
        "/api/_ui/v1/namespaces/", method="POST", args={"name": NAMESPACE_NAME, "groups": []}
    )
    assert collection_ns["name"] == NAMESPACE_NAME, collection_ns
    # Generate and upload a collection
    artifact = build_collection(
        "skeleton",
        config={
            "name": COLLECTION_NAME,
            "namespace": NAMESPACE_NAME,
            "tags": COLLECTION_TAGS,
            "description": COLLECTION_DESCRIPTION,
        },
    )
    resp = upload_artifact(admin_config, admin_client, artifact)
    resp = wait_for_task(admin_client, resp)
    """
    {'name': 'galaxy_fake_collection', 'namespace': 'ansible', 'description':
    'A collection to pretend to manage galaxy with infinidash support', 'type': 'collection',
    'latest_version': '1.0.0', 'avatar_url': '', 'contents': [], 'download_count':
    0, 'last_updated': '2023-11-10T19:44:46.243932Z', 'deprecated': False, 'tags':
    ['database', 'api', 'galaxy'], 'platforms': [], 'relevance': 0.0, 'search': ''}
    """
    # Create a legacy namespace
    role_ns = admin_client("/api/v1/namespaces/", method="POST", args={"name": NAMESPACE_NAME})
    assert role_ns["name"] == NAMESPACE_NAME, role_ns
    # Bind to the collection namespace as a provider
    admin_client(
        f"/api/v1/namespaces/{role_ns['id']}/providers/",
        method="POST",
        args={"id": collection_ns["id"]},
    )
    # Import a role
    ansible_galaxy(
        f"role import {GITHUB_USER} {GITHUB_REPO} --branch={BRANCH} --role-name={ROLE_NAME}",
        ansible_config=admin_config,
        force_token=True,
        cleanup=False,
        check_retcode=False,
    )
    """
    {'name': 'ansible-kubernetes-modules', 'namespace': 'ansible',
    'description': '"Pre-release Kubernetes modules"', 'type': 'role',
    'latest_version': '"0.4.0-alpha.0"', 'avatar_url': '', 'contents': [],
    'download_count': 0, 'last_updated': '2023-11-10T19:17:56.980903Z',
    'deprecated': False, 'tags': ['k8s', 'kubernetes', 'openshift', 'modules',
    'api'], 'platforms': [{'name': 'Fedora', 'versions': ['all']}, {'name':
    'Ubuntu', 'versions': ['all']}, {'name': 'EL', 'versions': ['all']}],
    'relevance': 0.0, 'search': ''}
    """


@pytest.fixture(scope="module")
def admin_client(ansible_config):
    admin_config = ansible_config("admin")
    return get_client(config=admin_config, request_token=False, require_auth=True)


@pytest.mark.deployment_community
def test_namespace_with_sql_search(admin_client):
    """Filter by namespace using default SQL search"""

    namespace = admin_client("/api/_ui/v1/search/?namespace=ansible")
    assert namespace["meta"]["count"] == 2


# IMPORTANT: Keep filtering by namespace to avoid including content from other tests


@pytest.mark.deployment_community
def test_name_with_sql_search(admin_client):
    """Test search."""
    name = admin_client(
        f"/api/_ui/v1/search/?search_type=sql&namespace=ansible&name={COLLECTION_NAME}"
    )
    assert name["meta"]["count"] == 1
    assert name["data"][0]["name"] == COLLECTION_NAME
    assert name["data"][0]["namespace"] == NAMESPACE_NAME
    assert name["data"][0]["tags"] == COLLECTION_TAGS
    assert name["data"][0]["description"] == COLLECTION_DESCRIPTION
    assert name["data"][0]["type"] == "collection"


@pytest.mark.deployment_community
def test_tags_with_sql_search(admin_client):
    """Test search."""
    tag_url = "/api/_ui/v1/search/?search_type=sql&namespace=ansible"
    for tag in COLLECTION_TAGS:
        tag_url += f"&tags={tag}"
    tags = admin_client(tag_url)
    assert tags["meta"]["count"] == 1
    assert tags["data"][0]["name"] == COLLECTION_NAME
    assert tags["data"][0]["namespace"] == NAMESPACE_NAME
    assert tags["data"][0]["tags"] == COLLECTION_TAGS
    assert tags["data"][0]["description"] == COLLECTION_DESCRIPTION
    assert tags["data"][0]["type"] == "collection"


@pytest.mark.deployment_community
def test_type_with_sql_search(admin_client):
    """Test search."""
    content_type = admin_client("/api/_ui/v1/search/?search_type=sql&namespace=ansible&type=role")
    assert content_type["meta"]["count"] == 1
    assert content_type["data"][0]["name"] == ROLE_NAME
    assert content_type["data"][0]["namespace"] == NAMESPACE_NAME
    assert content_type["data"][0]["tags"] == ROLE_TAGS
    assert content_type["data"][0]["description"] == ROLE_DESCRIPTION
    assert content_type["data"][0]["type"] == "role"


@pytest.mark.deployment_community
def test_platform_with_sql_search(admin_client):
    """Test search."""
    platform = admin_client("/api/_ui/v1/search/?search_type=sql&namespace=ansible&platform=fedora")
    assert platform["meta"]["count"] == 1
    assert platform["data"][0]["name"] == ROLE_NAME
    assert platform["data"][0]["namespace"] == NAMESPACE_NAME
    assert platform["data"][0]["tags"] == ROLE_TAGS
    assert platform["data"][0]["description"] == ROLE_DESCRIPTION
    assert platform["data"][0]["type"] == "role"


@pytest.mark.deployment_community
def test_deprecated_with_sql_search(admin_client):
    """Test search."""
    deprecated = admin_client(
        "/api/_ui/v1/search/?search_type=sql&namespace=ansible&deprecated=true"
    )
    assert deprecated["meta"]["count"] == 0


@pytest.mark.deployment_community
def test_keywords_with_sql_search(admin_client):
    """Test search."""
    keywords = admin_client(
        "/api/_ui/v1/search/?search_type=sql&namespace=ansible&keywords=infinidash"
    )
    assert keywords["meta"]["count"] == 1
    assert keywords["data"][0]["name"] == COLLECTION_NAME
    assert keywords["data"][0]["namespace"] == NAMESPACE_NAME
    assert keywords["data"][0]["tags"] == COLLECTION_TAGS
    assert keywords["data"][0]["description"] == COLLECTION_DESCRIPTION
    assert keywords["data"][0]["type"] == "collection"


@pytest.mark.deployment_community
def test_sorting_with_sql_search(admin_client):
    """Test search."""
    sorting = admin_client(
        "/api/_ui/v1/search/?search_type=sql&namespace=ansible&order_by=-last_updated"
    )
    assert sorting["meta"]["count"] == 2
    assert sorting["data"][0]["type"] == "role"
    assert sorting["data"][1]["type"] == "collection"


@pytest.mark.deployment_community
def test_facets_with_web_search(admin_client):
    """Search using vector websearch"""
    namespace = admin_client("/api/_ui/v1/search/?namespace=ansible")
    assert namespace["meta"]["count"] == 2

    # IMPORTANT: Keep filtering by namespace to avoid including content from other tests


@pytest.mark.deployment_community
def test_name_with_web_search(admin_client):
    """Search using vector websearch"""
    name = admin_client(f"/api/_ui/v1/search/?namespace=ansible&name={COLLECTION_NAME}")
    assert name["meta"]["count"] == 1
    assert name["data"][0]["name"] == COLLECTION_NAME
    assert name["data"][0]["namespace"] == NAMESPACE_NAME
    assert name["data"][0]["tags"] == COLLECTION_TAGS
    assert name["data"][0]["description"] == COLLECTION_DESCRIPTION
    assert name["data"][0]["type"] == "collection"


@pytest.mark.deployment_community
def test_tags_with_web_search(admin_client):
    """Search using vector websearch"""
    tag_url = "/api/_ui/v1/search/?namespace=ansible"
    for tag in COLLECTION_TAGS:
        tag_url += f"&tags={tag}"
    tags = admin_client(tag_url)
    assert tags["meta"]["count"] == 1
    assert tags["data"][0]["name"] == COLLECTION_NAME
    assert tags["data"][0]["namespace"] == NAMESPACE_NAME
    assert tags["data"][0]["tags"] == COLLECTION_TAGS
    assert tags["data"][0]["description"] == COLLECTION_DESCRIPTION
    assert tags["data"][0]["type"] == "collection"


@pytest.mark.deployment_community
def test_type_with_web_search(admin_client):
    """Search using vector websearch"""
    content_type = admin_client("/api/_ui/v1/search/?namespace=ansible&type=role")
    assert content_type["meta"]["count"] == 1
    assert content_type["data"][0]["name"] == ROLE_NAME
    assert content_type["data"][0]["namespace"] == NAMESPACE_NAME
    assert content_type["data"][0]["tags"] == ROLE_TAGS
    assert content_type["data"][0]["description"] == ROLE_DESCRIPTION
    assert content_type["data"][0]["type"] == "role"


@pytest.mark.deployment_community
def test_platform_with_web_search(admin_client):
    """Search using vector websearch"""
    platform = admin_client("/api/_ui/v1/search/?namespace=ansible&platform=fedora")
    assert platform["meta"]["count"] == 1
    assert platform["data"][0]["name"] == ROLE_NAME
    assert platform["data"][0]["namespace"] == NAMESPACE_NAME
    assert platform["data"][0]["tags"] == ROLE_TAGS
    assert platform["data"][0]["description"] == ROLE_DESCRIPTION
    assert platform["data"][0]["type"] == "role"


@pytest.mark.deployment_community
def test_deprecated_with_web_search(admin_client):
    """Search using vector websearch"""
    deprecated = admin_client("/api/_ui/v1/search/?namespace=ansible&deprecated=true")
    assert deprecated["meta"]["count"] == 0


@pytest.mark.deployment_community
def test_keywords_with_web_search(admin_client):
    """Search using vector websearch"""
    keywords = admin_client("/api/_ui/v1/search/?namespace=ansible&keywords=infinidash")
    assert keywords["meta"]["count"] == 1
    assert keywords["data"][0]["name"] == COLLECTION_NAME
    assert keywords["data"][0]["namespace"] == NAMESPACE_NAME
    assert keywords["data"][0]["tags"] == COLLECTION_TAGS
    assert keywords["data"][0]["description"] == COLLECTION_DESCRIPTION
    assert keywords["data"][0]["type"] == "collection"


@pytest.mark.deployment_community
def test_sorting_with_web_search(admin_client):
    """Search using vector websearch"""
    sorting = admin_client("/api/_ui/v1/search/?namespace=ansible&order_by=-last_updated")
    assert sorting["meta"]["count"] == 2
    assert sorting["data"][0]["type"] == "role"
    assert sorting["data"][1]["type"] == "collection"


@pytest.mark.deployment_community
def test_compound_query_with_web_search(admin_client):
    """Search using vector websearch"""
    for term in [
        "infinidash",
        "galaxy%20AND%20ansible",
        "infinidash%20OR%20java",
        "api%20-kubernetes",
    ]:
        websearch = admin_client(f"/api/_ui/v1/search/?namespace=ansible&keywords={term}")
        assert websearch["meta"]["count"] == 1
        assert websearch["data"][0]["name"] == COLLECTION_NAME
        assert websearch["data"][0]["namespace"] == NAMESPACE_NAME
        assert websearch["data"][0]["tags"] == COLLECTION_TAGS
        assert websearch["data"][0]["description"] == COLLECTION_DESCRIPTION
        assert websearch["data"][0]["type"] == "collection"

    for term in [
        "kubernetes",
        "kubernetes%20AND%20api",
        "kubernetes%20OR%20java",
        "api%20-infinidash",
    ]:
        websearch = admin_client(f"/api/_ui/v1/search/?namespace=ansible&keywords={term}")
        assert websearch["meta"]["count"] == 1
        assert websearch["data"][0]["name"] == ROLE_NAME
        assert websearch["data"][0]["namespace"] == NAMESPACE_NAME
        assert websearch["data"][0]["tags"] == ROLE_TAGS
        assert websearch["data"][0]["description"] == ROLE_DESCRIPTION
        assert websearch["data"][0]["type"] == "role"


@pytest.mark.deployment_community
def test_relevance_with_web_search(admin_client):
    """Search using vector websearch"""
    # Both has api tag and fedora term as a platform for role and description for collection
    keywords = admin_client(
        "/api/_ui/v1/search/?namespace=ansible" "&keywords=api%20AND%20fedora&order_by=-relevance"
    )
    assert keywords["meta"]["count"] == 2
    assert keywords["data"][0]["name"] == ROLE_NAME
    assert keywords["data"][1]["name"] == COLLECTION_NAME
    assert keywords["data"][0]["search"] != ""
    assert keywords["data"][0]["relevance"] != 0
