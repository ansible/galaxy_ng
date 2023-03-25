from galaxy_ng.tests.unit.api.base import BaseTestCase

from galaxy_ng.app.access_control.statements.roles import LOCKED_ROLES
from galaxy_ng.app.constants import PERMISSIONS


class TestPermissions(BaseTestCase):
    def test_permissions_defined_in_roles_have_description(self):
        role_permissions = set()
        for role in LOCKED_ROLES:
            for perm in LOCKED_ROLES[role]["permissions"]:
                role_permissions.add(perm)

        constant_permissions = {x for x in PERMISSIONS}

        # Synclist permissions shouldn't be exposed to the end user
        ignored_permissions = {
            'galaxy.delete_synclist',
            'galaxy.view_synclist',
            'galaxy.add_synclist',
            'galaxy.change_synclist'
        }

        constant_permissions = constant_permissions.union(ignored_permissions)

        diff = role_permissions.difference(constant_permissions)

        # All of the permissions used in roles must be declared in
        # galaxy_ng.app.constants.PERMISSIONS. If this fails, add
        # the missing permissions to that constant.
        self.assertEqual(diff, set())
