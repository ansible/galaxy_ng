"""test_ldap.py - tests related to ldap authentication.

See: AAH-1593
"""
import pytest
import logging

from ..utils import get_client


log = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def settings(ansible_config):
    config = ansible_config("admin")
    api_client = get_client(config, request_token=False, require_auth=True)
    return api_client("/api/automation-hub/_ui/v1/settings/")


@pytest.mark.standalone_only
@pytest.mark.ldap
def test_ldap_is_enabled(ansible_config, settings):
    """test whether ldap user can login"""
    if not settings.get("GALAXY_AUTH_LDAP_ENABLED"):
        pytest.skip("GALAXY_AUTH_LDAP_ENABLED is not enabled")

    config = ansible_config("admin")
    api_client = get_client(config, request_token=False, require_auth=True)
    assert (
        api_client("/api/automation-hub/_ui/v1/settings/")[
            "GALAXY_AUTH_LDAP_ENABLED"
        ]
        is True
    )


@pytest.mark.standalone_only
@pytest.mark.ldap
def test_ldap_login(ansible_config, settings):
    """test whether ldap user can login"""

    if not settings.get("GALAXY_AUTH_LDAP_ENABLED"):
        pytest.skip("GALAXY_AUTH_LDAP_ENABLED is not enabled")

    config = ansible_config("ldap")
    api_client = get_client(config, request_token=False, require_auth=True)

    # This test assumes the running ldap server is the
    # testing image from: rroemhild/test-openldap
    data = api_client("/api/automation-hub/_ui/v1/me/")
    assert data["username"] == "professor"
    assert data["email"] == "professor@planetexpress.com"
    assert data["first_name"] == "Hubert"
    assert data["last_name"] == "Farnsworth"
    assert data["groups"][0]["name"] == "admin_staff"
