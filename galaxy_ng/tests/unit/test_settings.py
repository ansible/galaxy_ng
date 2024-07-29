from django.test import TestCase
from django.conf import settings
from ansible_base.lib.dynamic_config import dynamic_settings


DAB_REQUIRED_SETTINGS = [key for key in dir(dynamic_settings) if key.isupper()]
RBAC_REQUIRED = [
    'ANSIBLE_BASE_TEAM_MODEL',
    'ANSIBLE_BASE_ROLE_CREATOR_NAME',
    'ANSIBLE_BASE_DELETE_REQUIRE_CHANGE',
    'ANSIBLE_BASE_ALLOW_TEAM_PARENTS',
    'ANSIBLE_BASE_ALLOW_TEAM_ORG_ADMIN',
    'ANSIBLE_BASE_MANAGED_ROLE_REGISTRY',
    'ANSIBLE_BASE_ALLOW_CUSTOM_ROLES',
    'ANSIBLE_BASE_ALLOW_CUSTOM_TEAM_ROLES',
    'ANSIBLE_BASE_ALLOW_SINGLETON_ROLES_API',
    'ANSIBLE_BASE_ALLOW_SINGLETON_USER_ROLES',
    'ANSIBLE_BASE_ALLOW_SINGLETON_TEAM_ROLES',
    'ANSIBLE_BASE_BYPASS_SUPERUSER_FLAGS',
    'ANSIBLE_BASE_EVALUATIONS_IGNORE_CONFLICTS',
]


class TestSetting(TestCase):
    def test_dab_settings_are_loaded(self):
        """Ensure all required settings from DAB are configured on Galaxy"""
        notset = object()
        for key in DAB_REQUIRED_SETTINGS + RBAC_REQUIRED:
            key_on_galaxy = settings.get(key, notset)
            self.assertIsNot(key_on_galaxy, notset)
