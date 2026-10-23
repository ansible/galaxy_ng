from importlib import import_module

from django.db import migrations
from django.test import TestCase


class TestRemoveStalePulpRbacIndexes(TestCase):
    """Test migration 0060_remove_stale_pulp_rbac_indexes."""

    def setUp(self):
        self.migration_module = import_module(
            'galaxy_ng.app.migrations.0060_remove_stale_pulp_rbac_indexes'
        )

    def test_migration_dependencies(self):
        Migration = self.migration_module.Migration
        assert hasattr(Migration, 'dependencies')
        assert ("galaxy", "0059_delete_system_auditor_role_definition") in Migration.dependencies

    def test_migration_operations(self):
        Migration = self.migration_module.Migration
        assert hasattr(Migration, 'operations')
        assert len(Migration.operations) == 1
        operation = Migration.operations[0]
        assert isinstance(operation, migrations.RunSQL)

    def test_migration_is_reversible(self):
        Migration = self.migration_module.Migration
        operation = Migration.operations[0]
        assert operation.reverse_sql is not None
        assert operation.reverse_sql != migrations.RunSQL.noop

    def test_drop_sql_targets_correct_indexes(self):
        expected_indexes = [
            "core_userrole_content_type_id_a2ff8402",
            "core_userrole_domain_id_f78b1c11",
            "core_userrole_role_id_8272b20d",
            "core_userrole_user_id_aca63c51",
            "core_userro_content_5c0477_idx",
            "core_grouprole_content_type_id_a80c1cfc",
            "core_grouprole_domain_id_9644db4b",
            "core_grouprole_group_id_09264d71",
            "core_grouprole_role_id_3c2c3564",
            "core_groupr_content_ea7d37_idx",
        ]
        assert self.migration_module.STALE_INDEXES == expected_indexes

    def test_drop_sql_uses_if_exists(self):
        for idx in self.migration_module.STALE_INDEXES:
            assert f"DROP INDEX IF EXISTS {idx};" in self.migration_module.drop_sql

    def test_reverse_sql_uses_if_not_exists(self):
        for idx in self.migration_module.STALE_INDEXES:
            assert f"CREATE INDEX IF NOT EXISTS {idx}" in self.migration_module.create_sql

    def test_only_targets_userrole_and_grouprole(self):
        for idx in self.migration_module.STALE_INDEXES:
            assert "userrole" in idx or "grouprole" in idx or "userro" in idx or "groupr" in idx
