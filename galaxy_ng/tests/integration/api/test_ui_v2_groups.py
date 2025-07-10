import json
import pytest

from galaxykit.client import BasicAuthClient

from ..utils.namespaces import generate_namespace


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_groups_create(galaxy_client, settings):
    """Test creating a group via the UI v2 groups endpoint"""

    if settings.get("IS_CONNECTED_TO_RESOURCE_SERVER"):
        pytest.skip("this test relies on local resource creation")

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    # Create a group via the _ui/v2/groups/ endpoint
    random_name = generate_namespace()
    group_data = ga.post(
        "/api/galaxy/_ui/v2/groups/",
        body=json.dumps({"name": random_name})
    )

    assert random_name == group_data["name"]
    assert "id" in group_data

    # Verify the group was created by retrieving it
    retrieved_group = ga.get(f"/api/galaxy/_ui/v2/groups/{group_data['id']}/")
    assert retrieved_group["name"] == random_name
    assert retrieved_group["id"] == group_data["id"]

    # Clean up - DELETE returns 204 with no content
    ga.delete(f"/api/galaxy/_ui/v2/groups/{group_data['id']}/", parse_json=False)


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_groups_list(galaxy_client, settings):
    """Test listing groups via the UI v2 groups endpoint"""

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    # Always test read operations as they should work regardless of resource server setting
    groups_list = ga.get("/api/galaxy/_ui/v2/groups/")
    assert "results" in groups_list

    # If connected to resource server, skip the create/test part
    if settings.get("IS_CONNECTED_TO_RESOURCE_SERVER"):
        pytest.skip("this test relies on local resource creation")

    # Create a test group
    random_name = generate_namespace()
    group_data = ga.post(
        "/api/galaxy/_ui/v2/groups/",
        body=json.dumps({"name": random_name})
    )

    # List groups and verify our group is in the list
    groups_list = ga.get(f"/api/galaxy/_ui/v2/groups/?name={random_name}")
    assert "results" in groups_list
    assert any(group["name"] == random_name for group in groups_list["results"])

    # Clean up
    ga.delete(f"/api/galaxy/_ui/v2/groups/{group_data['id']}/", parse_json=False)


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_groups_retrieve(galaxy_client, settings):
    """Test retrieving a specific group via the UI v2 groups endpoint"""

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    # If connected to resource server, skip the create/test part
    if settings.get("IS_CONNECTED_TO_RESOURCE_SERVER"):
        pytest.skip("this test relies on local resource creation")

    # Create a test group
    random_name = generate_namespace()
    group_data = ga.post(
        "/api/galaxy/_ui/v2/groups/",
        body=json.dumps({"name": random_name})
    )

    # Retrieve the group by ID
    retrieved_group = ga.get(f"/api/galaxy/_ui/v2/groups/{group_data['id']}/")
    assert retrieved_group["name"] == random_name
    assert retrieved_group["id"] == group_data["id"]

    # Clean up
    ga.delete(f"/api/galaxy/_ui/v2/groups/{group_data['id']}/", parse_json=False)


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_groups_update(galaxy_client, settings):
    """Test updating a group via the UI v2 groups endpoint"""

    if settings.get("IS_CONNECTED_TO_RESOURCE_SERVER"):
        pytest.skip("this test relies on local resource creation")

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    # Create a test group
    random_name = generate_namespace()
    group_data = ga.post(
        "/api/galaxy/_ui/v2/groups/",
        body=json.dumps({"name": random_name})
    )

    # Update the group name
    updated_name = generate_namespace()
    updated_group = ga.patch(
        f"/api/galaxy/_ui/v2/groups/{group_data['id']}/",
        body=json.dumps({"name": updated_name})
    )

    assert updated_group["name"] == updated_name
    assert updated_group["id"] == group_data["id"]

    # Verify the update by retrieving the group
    retrieved_group = ga.get(f"/api/galaxy/_ui/v2/groups/{group_data['id']}/")
    assert retrieved_group["name"] == updated_name

    # Clean up
    ga.delete(f"/api/galaxy/_ui/v2/groups/{group_data['id']}/", parse_json=False)


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_groups_delete(galaxy_client, settings):
    """Test deleting a group via the UI v2 groups endpoint"""

    if settings.get("IS_CONNECTED_TO_RESOURCE_SERVER"):
        pytest.skip("this test relies on local resource creation")

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    # Create a test group
    random_name = generate_namespace()
    group_data = ga.post(
        "/api/galaxy/_ui/v2/groups/",
        body=json.dumps({"name": random_name})
    )

    # Delete the group - should return 204 with no content
    response = ga.delete(f"/api/galaxy/_ui/v2/groups/{group_data['id']}/", parse_json=False)
    # The response should be an empty string for 204 responses
    assert response == ""


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_groups_filter_by_name(galaxy_client, settings):
    """Test filtering groups by name via the UI v2 groups endpoint"""

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    if settings.get("IS_CONNECTED_TO_RESOURCE_SERVER"):
        pytest.skip("this test relies on local resource creation")

    # Create test groups
    test_name1 = generate_namespace()
    test_name2 = generate_namespace()

    group_data1 = ga.post(
        "/api/galaxy/_ui/v2/groups/",
        body=json.dumps({"name": test_name1})
    )

    group_data2 = ga.post(
        "/api/galaxy/_ui/v2/groups/",
        body=json.dumps({"name": test_name2})
    )

    # Filter by name
    filtered_groups = ga.get(f"/api/galaxy/_ui/v2/groups/?name={test_name1}")
    assert "results" in filtered_groups
    assert len(filtered_groups["results"]) == 1
    assert filtered_groups["results"][0]["name"] == test_name1

    # Clean up
    ga.delete(f"/api/galaxy/_ui/v2/groups/{group_data1['id']}/", parse_json=False)
    ga.delete(f"/api/galaxy/_ui/v2/groups/{group_data2['id']}/", parse_json=False)


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_groups_ordering(galaxy_client, settings):
    """Test ordering groups by ID via the UI v2 groups endpoint"""

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    if settings.get("IS_CONNECTED_TO_RESOURCE_SERVER"):
        pytest.skip("this test relies on local resource creation")

    # Create test groups
    groups = []
    for i in range(3):
        group_name = f"test_group_{i}_{generate_namespace()}"
        group_data = ga.post(
            "/api/galaxy/_ui/v2/groups/",
            body=json.dumps({"name": group_name})
        )
        groups.append(group_data)

    # Get groups and verify they are ordered by ID
    groups_list = ga.get("/api/galaxy/_ui/v2/groups/")

    # Extract our test groups from the results
    test_groups = [g for g in groups_list["results"] if g["name"].startswith("test_group_")]

    # Verify ordering by ID (ascending)
    group_ids = [g["id"] for g in test_groups]
    assert group_ids == sorted(group_ids)

    # Clean up
    for group in groups:
        ga.delete(f"/api/galaxy/_ui/v2/groups/{group['id']}/", parse_json=False)


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_groups_pagination(galaxy_client, settings):
    """Test pagination of groups via the UI v2 groups endpoint"""

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    if settings.get("IS_CONNECTED_TO_RESOURCE_SERVER"):
        pytest.skip("this test relies on local resource creation")

    # Create multiple test groups
    created_groups = []
    for _i in range(3):
        group_name = generate_namespace()
        group_data = ga.post(
            "/api/galaxy/_ui/v2/groups/",
            body=json.dumps({"name": group_name})
        )
        created_groups.append(group_data)

    # Test pagination with page_size=2
    paginated_groups = ga.get("/api/galaxy/_ui/v2/groups/?page_size=2")
    assert "results" in paginated_groups
    assert len(paginated_groups["results"]) == 2
    assert "next" in paginated_groups
    assert "previous" in paginated_groups

    # Clean up
    for group in created_groups:
        ga.delete(f"/api/galaxy/_ui/v2/groups/{group['id']}/", parse_json=False)


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_groups_serializer_fields(galaxy_client, settings):
    """Test that the group serializer returns the expected fields"""

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    if settings.get("IS_CONNECTED_TO_RESOURCE_SERVER"):
        pytest.skip("this test relies on local resource creation")

    # Create a test group
    random_name = generate_namespace()
    group_data = ga.post(
        "/api/galaxy/_ui/v2/groups/",
        body=json.dumps({"name": random_name})
    )

    # Verify the serializer returns expected fields
    expected_fields = {"id", "name"}
    assert set(group_data.keys()) == expected_fields
    assert isinstance(group_data["id"], int)
    assert isinstance(group_data["name"], str)

    # Clean up
    ga.delete(f"/api/galaxy/_ui/v2/groups/{group_data['id']}/", parse_json=False)


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_groups_put_update(galaxy_client, settings):
    """Test updating a group via PUT method"""

    if settings.get("IS_CONNECTED_TO_RESOURCE_SERVER"):
        pytest.skip("this test relies on local resource creation")

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    # Create a test group
    random_name = generate_namespace()
    group_data = ga.post(
        "/api/galaxy/_ui/v2/groups/",
        body=json.dumps({"name": random_name})
    )

    # Update the group name via PUT
    updated_name = generate_namespace()
    updated_group = ga.put(
        f"/api/galaxy/_ui/v2/groups/{group_data['id']}/",
        body=json.dumps({"name": updated_name})
    )

    assert updated_group["name"] == updated_name
    assert updated_group["id"] == group_data["id"]

    # Verify the update by retrieving the group
    retrieved_group = ga.get(f"/api/galaxy/_ui/v2/groups/{group_data['id']}/")
    assert retrieved_group["name"] == updated_name

    # Clean up
    ga.delete(f"/api/galaxy/_ui/v2/groups/{group_data['id']}/", parse_json=False)


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_groups_empty_filter_result(galaxy_client):
    """Test filtering groups with no matching results"""

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    # Filter by a name that doesn't exist
    filtered_groups = ga.get("/api/galaxy/_ui/v2/groups/?name=nonexistent_group_name")
    assert "results" in filtered_groups
    assert len(filtered_groups["results"]) == 0
    assert filtered_groups["count"] == 0
