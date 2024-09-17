import copy
import json
import os

import pytest

from galaxykit.client import BasicAuthClient

from galaxy_ng.tests.integration.utils.namespaces import generate_namespace


pytestmark = pytest.mark.qa  # noqa: F821


class GatewayUserAttributes:
    username = None
    user_client = None
    gateway_v1_me = None
    galaxy_v1_me = None
    galaxy_v2_me = None


@pytest.fixture
def gateway_admin_client(galaxy_client):
    if not os.environ.get('AAP_GATEWAY_ADMIN_USERNAME'):
        pytest.skip("AAP_GATEWAY_ADMIN_USERNAME not set")

    gc = galaxy_client("admin", ignore_cache=True)
    username = os.environ.get('AAP_GATEWAY_ADMIN_USERNAME')
    password = os.environ.get('AAP_GATEWAY_ADMIN_PASSWORD')
    return BasicAuthClient(gc.galaxy_root, username, password)


@pytest.fixture
def random_gateway_user(gateway_admin_client, galaxy_client, random_username):

    # make the user in the gateway
    gateway_admin_client.post(
        '/api/gateway/v1/users/',
        body=json.dumps({'username': random_username, 'password': 'redhat1234'})
    )

    # access galaxy as the user to process claims ...
    gc = galaxy_client("admin", ignore_cache=True)
    uc = BasicAuthClient(gc.galaxy_root, random_username, 'redhat1234')

    gu = GatewayUserAttributes()
    gu.username = random_username
    gu.user_client = uc
    gu.gateway_v1_me = uc.get('/api/gateway/v1/me/')['results'][0]
    gu.galaxy_v1_me = uc.get('/api/galaxy/_ui/v1/me/')
    gu.galaxy_v2_me = uc.get('/api/galaxy/_ui/v2/me/')

    return gu


@pytest.fixture
def gateway_user_factory(gateway_admin_client, galaxy_client):

    def _create_user():
        username = 'user_' + generate_namespace()

        # make the user in the gateway
        gateway_admin_client.post(
            '/api/gateway/v1/users/',
            body=json.dumps({'username': username, 'password': 'redhat1234'})
        )

        # access galaxy as the user to process claims ...
        gc = galaxy_client("admin", ignore_cache=True)
        uc = BasicAuthClient(gc.galaxy_root, username, 'redhat1234')

        gu = GatewayUserAttributes()
        gu.username = username
        gu.user_client = uc
        gu.gateway_v1_me = uc.get('/api/gateway/v1/me/')['results'][0]
        gu.galaxy_v1_me = uc.get('/api/galaxy/_ui/v1/me/')
        gu.galaxy_v2_me = uc.get('/api/galaxy/_ui/v2/me/')

        return gu

    return _create_user


@pytest.mark.deployment_standalone
@pytest.mark.parametrize(
    'users_endpoint',
    [
        "/api/galaxy/_ui/v1/users/",
        "/api/galaxy/_ui/v2/users/",
    ]
)
@pytest.mark.parametrize(
    'verb',
    [
        'PUT',
        'PATCH'
    ]
)
def test_aap_galaxy_normal_user_can_not_demote_superuser(
    users_endpoint,
    verb,
    settings,
    gateway_admin_client,
    gateway_user_factory,
):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is not False:
        pytest.skip("ALLOW_LOCAL_RESOURCE_MANAGEMENT=true")

    u1 = gateway_user_factory()
    u2 = gateway_user_factory()

    # make user1 a superuser & process claims
    url = '/api/gateway/v1/users/' + str(u1.gateway_v1_me['id']) + "/"
    resp = gateway_admin_client.patch(url, json={'is_superuser': True})
    assert resp['is_superuser'], resp
    me2 = u1.user_client.get('/api/galaxy/_ui/v2/me/')
    assert me2['is_superuser'], me2

    # try to demote user1 on galaxy as user2
    user_url = users_endpoint + str(u1.galaxy_v2_me['id']) + '/'

    if verb == 'PUT':
        payload = copy.deepcopy(u1.galaxy_v2_me)
        payload['is_superuser'] = False
    else:
        payload = {'is_superuser': False}

    func = getattr(u2.user_client, verb.lower())
    resp = func(user_url, json=payload)
    assert "You do not have permission to perform this action" in str(resp)


@pytest.mark.deployment_standalone
@pytest.mark.parametrize(
    'users_endpoint',
    [
        "/api/galaxy/_ui/v1/users/",
        "/api/galaxy/_ui/v2/users/",
    ]
)
def test_aap_galaxy_local_resource_management_setting_gates_user_creation(
    users_endpoint,
    settings,
    gateway_admin_client,
    random_username
):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is not False:
        pytest.skip("ALLOW_LOCAL_RESOURCE_MANAGEMENT=true")

    # make sure the user can't be created directly in galaxy ...
    resp = gateway_admin_client.post(
        users_endpoint,
        body=json.dumps({'username': random_username, 'password': 'redhat1234'})
    )
    assert "You do not have permission to perform this action" in str(resp)


@pytest.mark.deployment_standalone
@pytest.mark.parametrize(
    'users_endpoint',
    [
        "/api/galaxy/_ui/v1/users",
        "/api/galaxy/_ui/v2/users",
    ]
)
@pytest.mark.parametrize(
    'verb',
    ['PUT', 'PATCH']
)
@pytest.mark.parametrize(
    'field',
    ['id', 'username', 'password', 'first_name', 'last_name']
)
def test_aap_galaxy_local_resource_management_setting_gates_field_modification(
    users_endpoint,
    verb,
    field,
    settings,
    gateway_admin_client,
    random_gateway_user,
):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is not False:
        pytest.skip("ALLOW_LOCAL_RESOURCE_MANAGEMENT=true")

    uid = random_gateway_user.galaxy_v2_me['id']
    user_url = f'{users_endpoint}/{uid}/'
    admin_func = getattr(gateway_admin_client, verb.lower())

    if verb == 'PUT':
        payload = copy.deepcopy(random_gateway_user.galaxy_v2_me)
        payload[field] = "foobar12345"
    else:
        payload = {field: "foobar12345"}
    resp = admin_func(user_url, json=payload)
    assert "You do not have permission to perform this action" in str(resp)


@pytest.mark.deployment_standalone
@pytest.mark.parametrize(
    'users_endpoint',
    [
        "/api/galaxy/_ui/v1/users",
        "/api/galaxy/_ui/v2/users",
    ]
)
def test_aap_galaxy_local_resource_management_setting_gates_deletion(
    users_endpoint,
    settings,
    gateway_admin_client,
    random_gateway_user,
):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is not False:
        pytest.skip("ALLOW_LOCAL_RESOURCE_MANAGEMENT=true")

    uid = random_gateway_user.galaxy_v2_me['id']
    user_url = f'{users_endpoint}/{uid}/'
    resp = gateway_admin_client.delete(user_url)
    assert "You do not have permission to perform this action" in str(resp)


@pytest.mark.deployment_standalone
@pytest.mark.parametrize(
    'verb',
    ['PUT', 'PATCH']
)
def test_aap_galaxy_superuser_management(
    verb,
    settings,
    gateway_admin_client,
    random_gateway_user
):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is not False:
        pytest.skip("ALLOW_LOCAL_RESOURCE_MANAGEMENT=true")

    ga = gateway_admin_client
    uc = random_gateway_user.user_client
    galaxy_user_data = random_gateway_user.galaxy_v2_me

    # ensure the user is not a superuser by default ...
    assert random_gateway_user.gateway_v1_me['is_superuser'] is False
    assert random_gateway_user.galaxy_v1_me['is_superuser'] is False
    assert random_gateway_user.galaxy_v2_me['is_superuser'] is False

    # try to promote&demote the user as the admin ...
    uid = galaxy_user_data['id']
    user_url = f'/api/galaxy/_ui/v2/users/{uid}/'
    admin_func = getattr(ga, verb.lower())
    for value in [True, False]:
        if verb == 'PUT':
            payload = copy.deepcopy(galaxy_user_data)
            payload['is_superuser'] = value
        else:
            payload = {'is_superuser': value}
        resp = admin_func(user_url, json=payload)
        assert resp.get('is_superuser') is value, resp

    # make sure the user can not promote themself ...
    user_func = getattr(uc, verb.lower())
    if verb == 'PUT':
        payload = copy.deepcopy(galaxy_user_data)
        payload['is_superuser'] = True
    else:
        payload = {'is_superuser': True}
    resp = user_func(user_url, json=payload)
    assert "You do not have permission to perform this action" in str(resp)

    # make sure the user can demote themself ...
    ga.patch(user_url, json={"is_superuser": True})
    if verb == 'PUT':
        payload = copy.deepcopy(galaxy_user_data)
        payload['is_superuser'] = False
    else:
        payload = {'is_superuser': False}
    resp = user_func(user_url, json=payload)
    assert resp.get('is_superuser') is False, resp
