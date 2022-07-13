"""test_ldap.py - tests related to ldap authentication.

See: AAH-1593
"""
import pytest
import logging

from ..utils import get_client


log = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def config(ansible_config):
    return ansible_config("ansible_partner")


@pytest.fixture(scope="function")
def config_ldap(ansible_config):
    class AnsibleConfigLDAP(ansible_config):
        def __getitem__(self, key):
            if key == "username":
                return "professor"
            if key == "password":
                return "professor"
            return super().__getitem__(key)

    return AnsibleConfigLDAP("ansible_partner")


@pytest.fixture(scope="function")
def ldap_api_client(config_ldap):
    return get_client(
        config=config_ldap, request_token=False, require_auth=True
    )


@pytest.fixture(scope="function")
def api_client(config):
    return get_client(config=config, request_token=True, require_auth=True)


@pytest.fixture(scope="function")
def settings(api_client):
    return api_client("/api/automation-hub/_ui/v1/settings/")


@pytest.mark.standalone_only
def test_ldap_is_enabled(api_client, settings):
    """test whether ldap user can login"""
    if not settings.get("GALAXY_AUTH_LDAP_ENABLED"):
        pytest.skip("GALAXY_AUTH_LDAP_ENABLED is not enabled")

    assert (
        api_client("/api/automation-hub/_ui/v1/settings/")[
            "GALAXY_AUTH_LDAP_ENABLED"
        ]
        is True
    )


@pytest.mark.standalone_only
def test_ldap_login(ldap_api_client, settings):
    """test whether ldap user can login"""
    if not settings.get("GALAXY_AUTH_LDAP_ENABLED"):
        pytest.skip("GALAXY_AUTH_LDAP_ENABLED is not enabled")

    # This test assumes the running ldap server is the
    # testing image from: rroemhild/test-openldap
    data = ldap_api_client("/api/automation-hub/_ui/v1/me/")
    assert data["username"] == "professor"
    assert data["email"] == "professor@planetexpress.com"
    assert data["first_name"] == "Hubert"
    assert data["last_name"] == "Farnsworth"
    assert data["groups"][0]["name"] == "admin_staff"
