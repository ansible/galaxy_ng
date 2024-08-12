import pytest
from galaxykit.utils import GalaxyClientError
import uuid


@pytest.fixture
def test_group(settings, galaxy_client):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip(reason="ALLOW_LOCAL_RESOURCE_MANAGEMENT=false")

    gc = galaxy_client("admin")

    return gc.get("_ui/v1/groups/?name=ns_group_for_tests")["data"][0]


@pytest.fixture
def test_user(settings, galaxy_client):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip(reason="ALLOW_LOCAL_RESOURCE_MANAGEMENT=false")

    gc = galaxy_client("admin")

    return gc.get("_ui/v1/users/?username=admin")["data"][0]


@pytest.mark.parametrize(
    'url',
    [
        "_ui/v1/groups/",
        "pulp/api/v3/groups/",
    ]
)
@pytest.mark.deployment_standalone
def test_dab_groups_are_read_only(settings, galaxy_client, url, test_group):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') in [None, True]:
        pytest.skip(reason="ALLOW_LOCAL_RESOURCE_MANAGEMENT=true")

    gc = galaxy_client("admin")

    group_pk = test_group["id"]

    with pytest.raises(GalaxyClientError) as ctx:
        gc.post(url, body={"name": str(uuid.uuid4())})

    assert ctx.value.args[0] == 403

    # Apparently we don't support updating on the ui api?
    if "pulp/api" in url:
        detail = url + f"{group_pk}/"
        with pytest.raises(GalaxyClientError) as ctx:
            gc.patch(detail, body={"name": str(uuid.uuid4())})

        assert ctx.value.args[0] == 403

        detail = url + f"{group_pk}/"
        with pytest.raises(GalaxyClientError) as ctx:
            gc.put(detail, body={"name": str(uuid.uuid4())})

    assert ctx.value.args[0] == 403

    detail = url + f"{group_pk}/"
    with pytest.raises(GalaxyClientError) as ctx:
        gc.delete(detail)

    assert ctx.value.args[0] == 403


@pytest.mark.parametrize(
    'url',
    [
        "_ui/v1/users/",
        "pulp/api/v3/users/",
    ]
)
@pytest.mark.deployment_standalone
def test_dab_users_are_read_only(settings, galaxy_client, url, test_user):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') in [None, True]:
        pytest.skip(reason="ALLOW_LOCAL_RESOURCE_MANAGEMENT=true")

    gc = galaxy_client("admin")

    user_pk = test_user["id"]

    with pytest.raises(GalaxyClientError) as ctx:
        gc.post(url, body={"username": str(uuid.uuid4())})

    assert ctx.value.args[0] == 403

    detail = url + f"{user_pk}/"
    with pytest.raises(GalaxyClientError) as ctx:
        gc.patch(detail, body={"username": str(uuid.uuid4())})

    assert ctx.value.args[0] == 403

    detail = url + f"{user_pk}/"
    with pytest.raises(GalaxyClientError) as ctx:
        gc.put(detail, body={"username": str(uuid.uuid4())})

    assert ctx.value.args[0] == 403

    detail = url + f"{user_pk}/"
    with pytest.raises(GalaxyClientError) as ctx:
        gc.delete(detail)

    assert ctx.value.args[0] == 403


@pytest.mark.deployment_standalone
def test_dab_cant_modify_group_memberships(settings, galaxy_client, test_user, test_group):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') in [None, True]:
        pytest.skip(reason="ALLOW_LOCAL_RESOURCE_MANAGEMENT=true")

    gc = galaxy_client("admin")

    hub_user_detail = f"_ui/v1/users/{test_user['id']}/"
    with pytest.raises(GalaxyClientError) as ctx:
        gc.patch(hub_user_detail, body={
            "groups": [{
                "id": test_group["id"],
                "name": test_group["name"],
            }]
        })

    assert ctx.value.args[0] == 403

    pulp_group_users = f"pulp/api/v3/groups/{test_group['id']}/users/"

    with pytest.raises(GalaxyClientError) as ctx:
        gc.post(pulp_group_users, body={"username": test_user["username"]})

    assert ctx.value.args[0] == 403


@pytest.mark.deployment_standalone
def test_dab_can_modify_roles(settings, galaxy_client, test_user, test_group):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') in [None, True]:
        pytest.skip(reason="ALLOW_LOCAL_RESOURCE_MANAGEMENT=true")

    gc = galaxy_client("admin")

    gc.post(f"pulp/api/v3/groups/{test_group['id']}/roles/", body={
        "content_object": None,
        "role": "galaxy.content_admin",
    })

    gc.post(f"pulp/api/v3/users/{test_user['id']}/roles/", body={
        "content_object": None,
        "role": "galaxy.content_admin",
    })
