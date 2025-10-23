"""
Test for migration 0054 - migrate_role_assignments function.

This test reproduces an issue where GroupRole objects created without
corresponding RoleTeamAssignment objects (as would happen during upgrade)
cause an AttributeError when the migration tries to access group_role.id.
"""

import pytest
from django.apps import apps
from django.contrib.auth.models import Group

from pulpcore.plugin.models.role import GroupRole, Role
from galaxy_ng.app.signals.handlers import pulp_rbac_signals, dab_rbac_signals
from galaxy_ng.app.migrations._dab_rbac import (
    split_pulp_roles, copy_roles_to_role_definitions, migrate_role_assignments
)

from ansible_base.rbac.models import RoleDefinition, RoleTeamAssignment


@pytest.mark.django_db
class TestMigrateRoleAssignmentsMigration:
    """Test the migrate_role_assignments migration function."""

    @pytest.mark.parametrize('role_name',
        [
            "galaxy.content_admin",
            "galaxy.collection_admin",
            "galaxy.collection_publisher",  # hits old ValueError AAP-56523
            "galaxy.collection_curator",
            # The rest are mostly redundant, so not enabling for runtime
            "galaxy.collection_remote_owner",  # hits old ValueError AAP-56523
            "galaxy.ansible_repository_owner",  # hits old ValueError AAP-56523
            "galaxy.collection_namespace_owner",  # hits old ValueError AAP-56523
            "galaxy.execution_environment_admin",
            "galaxy.execution_environment_publisher",  # hits old ValueError AAP-56523
            "galaxy.execution_environment_namespace_owner",  # hits old ValueError AAP-56523
            "galaxy.execution_environment_collaborator",  # hits old ValueError AAP-56523
            "galaxy.group_admin",
            "galaxy.user_admin",
            "galaxy.synclist_owner",
            "galaxy.task_admin",  # hits old ValueError AAP-56523
            "galaxy.auditor"
        ]
    )
    def test_migrate_global_group_roles(self, role_name):
        """
        This simulates the state during an upgrade where GroupRole objects exist
        but the DAB RBAC RoleTeamAssignment objects haven't been created yet.
        """
        with pulp_rbac_signals(), dab_rbac_signals():
            # Create objects pre-migration
            group = Group.objects.create(name='test_group')

            for rd in RoleDefinition.objects.all():
                rd.delete()

            # Assign every role in the system to test_group
            role = Role.objects.get(name=role_name)
            GroupRole.objects.create(
                role=role,
                group=group,
                content_type=None,  # assigned globally
                object_id=None  # no object
            )

            assert RoleTeamAssignment.objects.count() == 0

            # Simulate data migration
            split_pulp_roles(apps, None)
            copy_roles_to_role_definitions(apps, None)
            migrate_role_assignments(apps, None)

            no_dab_roles = [
                'galaxy.group_admin',
                'galaxy.user_admin',
                'galaxy.synclist_owner',
                'galaxy.auditor'
            ]

            if role_name in no_dab_roles:
                assert RoleTeamAssignment.objects.count() == 0
            else:
                assert RoleTeamAssignment.objects.count() == 1
