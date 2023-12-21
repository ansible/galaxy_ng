"""test_ldap.py - tests related to ldap authentication.

See: AAH-1593

These tests cases must run and pass also when
the LDAP server has REFERRALS enabled
python-ldap can't chase the referral links
so the galaxy system might be set with
GALAXY_LDAP_DISABLE_REFERRALS=True
See: AAH-2150
"""
import pytest
import logging

from galaxykit.users import get_me

log = logging.getLogger(__name__)


def is_present(group, groups):
    """looks for a given group in the groups list

    Args:
        group: The group to be found.
        groups: List of groups to iterate over.

    Returns:
        True of group is found in groups, False otherwise
    """
    group_found = False
    for _group in groups:
        if _group["name"] == group:
            group_found = True
    return group_found


@pytest.mark.deployment_standalone
@pytest.mark.iqe_ldap
def test_ldap_is_enabled(skip_if_ldap_disabled, galaxy_client):
    """test whether ldap user can login"""
    gc = galaxy_client("admin")
    gc.get_settings()
    assert gc.get_settings()["GALAXY_AUTH_LDAP_ENABLED"] is True


@pytest.mark.deployment_standalone
@pytest.mark.iqe_ldap
def test_ldap_user_can_log_in(skip_if_ldap_disabled, galaxy_client, ldap_user):
    """
    Verifies that a user on LDAP server can log into automation hub
    """
    username = "awong"
    user = ldap_user(username)
    gc = galaxy_client(user)
    resp = get_me(gc)
    assert resp["username"] == username


@pytest.mark.deployment_standalone
@pytest.mark.iqe_ldap
def test_ldap_admin_user_is_superuser_in_ahub(skip_if_ldap_disabled, galaxy_client, ldap_user):
    """
    Verifies that a user from an admin group on LDAP server is a superuser in ahub
    PULP_AUTH_LDAP_USER_FLAGS_BY_GROUP__is_superuser="cn=bobsburgers_admins,cn=groups,cn=accounts,dc=testing,dc=ansible,dc=com"
    """
    username = "bbelcher"
    user = ldap_user(username)
    gc = galaxy_client(user)
    resp = get_me(gc)
    assert resp["username"] == username
    assert resp["is_superuser"] is True


@pytest.mark.deployment_standalone
@pytest.mark.iqe_ldap
def test_ldap_personal_information_synced(skip_if_ldap_disabled, galaxy_client, ldap_user):
    """
    Verifies that personal information is correctly imported to ahub
    PULP_AUTH_LDAP_USER_ATTR_MAP = {first_name = "givenName", last_name = "sn", email = "mail"}
    """
    username = "brodriguez"
    user = ldap_user(username)
    gc = galaxy_client(user)
    resp = get_me(gc)
    assert resp["username"] == username
    assert resp["is_superuser"] is False
    assert resp["first_name"] == "Bender"
    assert resp["last_name"] == "Rodriguez"
    assert resp["email"] == "brodriguez@testing.ansible.com"


@pytest.mark.deployment_standalone
@pytest.mark.iqe_ldap
def test_ldap_groups_synced(skip_if_ldap_disabled, settings, galaxy_client, ldap_user):
    """
    Verifies that groups are correctly created in ahub
    PULP_AUTH_LDAP_MIRROR_GROUPS=true
    """
    if settings.get("GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS"):
        pytest.skip("GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS is enabled")

    username = "bstrickland"
    # bstrickland belongs to groups stricklandpropane, stricklandpropane_admins
    user = ldap_user(username)
    gc = galaxy_client(user, ignore_cache=True)
    resp = get_me(gc)
    assert resp["username"] == username
    groups = resp["groups"]
    assert is_present("stricklandpropane", groups)
    assert is_present("stricklandpropane_admins", groups)


@pytest.mark.deployment_standalone
@pytest.mark.iqe_ldap
def test_ldap_mirror_only_existing_groups(skip_if_ldap_disabled,
                                          settings,
                                          galaxy_client,
                                          ldap_user):
    """Ensure that GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS works as expected."""
    if not settings.get("GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS"):
        pytest.skip("GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS is not enabled")
    # bstrickland belongs to groups stricklandpropane, stricklandpropane_admins
    username = "bstrickland"
    user = ldap_user(username)
    gc = galaxy_client(user, ignore_cache=True)
    resp = get_me(gc)
    assert resp["username"] == username
    # This user is member only of "ships_crew" group that doesnt exist
    # so this user will not get groups mirrored.
    assert len(resp["groups"]) == 0


@pytest.mark.deployment_standalone
@pytest.mark.iqe_ldap
def test_ldap_ignored_groups(skip_if_ldap_disabled, galaxy_client, ldap_user):
    """
    Verifies that groups can be ignored and not created in ahub
    PULP_AUTH_LDAP_MIRROR_GROUPS_EXCEPT=['dreamland']
    """

    username = "marcher"
    user = ldap_user(username)
    gc = galaxy_client(user)
    resp = get_me(gc)
    assert resp["username"] == username
    groups = resp["groups"]
    assert not is_present("dreamland", groups)


@pytest.mark.deployment_standalone
@pytest.mark.iqe_ldap
def test_ldap_user_with_no_group(skip_if_ldap_disabled, galaxy_client, ldap_user):
    """
    Verifies that users that does not belong to any group are also synced
    """
    username = "saml_user"
    user = ldap_user(username)
    gc = galaxy_client(user)
    resp = get_me(gc)
    assert resp["username"] == username
    assert resp["groups"] == []
