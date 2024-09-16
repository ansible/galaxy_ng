import pytest

from galaxykit.client import BasicAuthClient
from galaxy_ng.tests.integration.utils.ldap import LDAPAdminClient

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.ldap
@pytest.mark.min_hub_version("4.10dev")
def test_aap_renamed_ldap_user(
    ansible_config,
    settings,
    random_username,
):

    if not settings.get("GALAXY_AUTH_LDAP_ENABLED"):
        pytest.skip("GALAXY_AUTH_LDAP_ENABLED is not enabled")

    admin_config = ansible_config("admin")
    admin_client = BasicAuthClient(
        admin_config.get('url'),
        admin_config.get('username'),
        admin_config.get('password'),
    )

    # make the user in ldap
    ldap_admin = LDAPAdminClient()
    ldap_admin.create_user(username=random_username, password=random_username)

    # login to galaxy as the user
    ldap_client = BasicAuthClient(
        admin_config.get('url'),
        random_username,
        random_username,
    )
    v2me = ldap_client.get('_ui/v2/me/')
    uid = v2me['id']
    assert v2me['username'] == random_username

    # change the username inside galaxy to the prefixed username ..
    migrated_username = 'galaxy_' + random_username
    resp = admin_client.patch(f'_ui/v2/users/{uid}/', json={'username': migrated_username})
    assert resp['id'] == uid
    assert resp['username'] == migrated_username

    # can we auth with the migrated username?
    migrated_client = BasicAuthClient(
        admin_config.get('url'),
        migrated_username,
        random_username,
    )
    v2me_test1 = migrated_client.get('_ui/v2/me/')
    assert v2me_test1['id'] == uid
    assert v2me_test1['username'] == migrated_username

    # can we still login with the old username?
    v2me_test2 = ldap_client.get('_ui/v2/me/')
    assert v2me_test2['id'] == uid
    assert v2me_test2['username'] == migrated_username
