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

from ..utils import get_client


log = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def settings(ansible_config):
    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(config, request_token=False, require_auth=True)
    return api_client(f"{api_prefix}/_ui/v1/settings/")


@pytest.mark.ldap
def test_ldap_is_enabled(ansible_config, settings):
    """test whether ldap user can login"""
    if not settings.get("GALAXY_AUTH_LDAP_ENABLED"):
        pytest.skip("GALAXY_AUTH_LDAP_ENABLED is not enabled")

    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(config, request_token=False, require_auth=True)
    assert api_client(f"{api_prefix}/_ui/v1/settings/")["GALAXY_AUTH_LDAP_ENABLED"] is True


@pytest.mark.ldap
def test_ldap_login(ansible_config, settings):
    """test whether ldap user can login"""

    if not settings.get("GALAXY_AUTH_LDAP_ENABLED"):
        pytest.skip("GALAXY_AUTH_LDAP_ENABLED is not enabled")

    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(config, request_token=False, require_auth=True)

    # This test assumes the running ldap server is the
    # testing image from: rroemhild/test-openldap
    data = api_client(f"{api_prefix}/_ui/v1/me/")
    assert data["username"] == "professor"
    assert data["email"] == "professor@planetexpress.com"
    assert data["first_name"] == "Hubert"
    assert data["last_name"] == "Farnsworth"
    # This group is pre-created on hub
    assert data["groups"][0]["name"] == "admin_staff"


@pytest.mark.ldap
def test_ldap_mirror_only_existing_groups(ansible_config, settings):
    """Ensure that GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS works as expected."""

    if not settings.get("GALAXY_AUTH_LDAP_ENABLED"):
        pytest.skip("GALAXY_AUTH_LDAP_ENABLED is not enabled")

    if not settings.get("GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS"):
        pytest.skip("GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS is not enabled")

    config = ansible_config("ldap_non_admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(config, request_token=False, require_auth=True)

    # This test assumes the running ldap server is the
    # testing image from: rroemhild/test-openldap
    data = api_client(f"{api_prefix}/_ui/v1/me/")
    assert data["username"] == "fry"
    assert data["email"] == "fry@planetexpress.com"
    assert data["first_name"] == "Philip"
    assert data["last_name"] == "Fry"
    # This user is member only of "ships_crew" group that doesnt exist
    # so this user will not get groups mirrored.
    assert len(data["groups"]) == 0
