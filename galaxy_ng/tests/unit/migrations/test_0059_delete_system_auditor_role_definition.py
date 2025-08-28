from unittest.mock import Mock
from django.db import migrations


class TestDeleteSystemAuditorRoleDefinitionMigration:
    """Test migration 0059_delete_system_auditor_role_definition."""

    def test_delete_system_auditor_role_definition_exists(self):
        """Test deleting System Auditor role definition when it exists."""
        # Import the migration module using importlib to handle numeric module name
        import importlib
        migration_module = importlib.import_module(
            'galaxy_ng.app.migrations.0059_delete_system_auditor_role_definition'
        )
        delete_system_auditor_role_definition = (
            migration_module.delete_system_auditor_role_definition
        )

        # Mock the apps and schema_editor
        mock_apps = Mock()
        mock_schema_editor = Mock()

        # Mock the RoleDefinition model
        mock_role_definition_model = Mock()
        mock_apps.get_model.return_value = mock_role_definition_model

        # Mock an existing System Auditor role
        mock_system_auditor_role = Mock()
        mock_role_definition_model.objects.filter.return_value.first.return_value = (
            mock_system_auditor_role
        )

        # Run the migration function
        delete_system_auditor_role_definition(mock_apps, mock_schema_editor)

        # Verify the correct calls were made
        mock_apps.get_model.assert_called_once_with("dab_rbac", "RoleDefinition")
        mock_role_definition_model.objects.filter.assert_called_once_with(name="System Auditor")
        mock_role_definition_model.objects.filter.return_value.first.assert_called_once()
        mock_system_auditor_role.delete.assert_called_once()

    def test_delete_system_auditor_role_definition_not_exists(self):
        """Test migration when System Auditor role definition doesn't exist."""
        # Import the migration module using importlib to handle numeric module name
        import importlib
        migration_module = importlib.import_module(
            'galaxy_ng.app.migrations.0059_delete_system_auditor_role_definition'
        )
        delete_system_auditor_role_definition = (
            migration_module.delete_system_auditor_role_definition
        )

        # Mock the apps and schema_editor
        mock_apps = Mock()
        mock_schema_editor = Mock()

        # Mock the RoleDefinition model
        mock_role_definition_model = Mock()
        mock_apps.get_model.return_value = mock_role_definition_model

        # Mock no existing System Auditor role
        mock_role_definition_model.objects.filter.return_value.first.return_value = None

        # Run the migration function
        delete_system_auditor_role_definition(mock_apps, mock_schema_editor)

        # Verify the correct calls were made
        mock_apps.get_model.assert_called_once_with("dab_rbac", "RoleDefinition")
        mock_role_definition_model.objects.filter.assert_called_once_with(name="System Auditor")
        mock_role_definition_model.objects.filter.return_value.first.assert_called_once()

        # No delete should be called since the role doesn't exist

    def test_migration_dependencies(self):
        """Test that migration has correct dependencies."""
        import importlib
        migration_module = importlib.import_module(
            'galaxy_ng.app.migrations.0059_delete_system_auditor_role_definition'
        )
        Migration = migration_module.Migration

        assert hasattr(Migration, 'dependencies')
        assert ("galaxy", "0058_remove_galaxy_team_member_role") in Migration.dependencies
        assert ("dab_rbac", "0003_alter_dabpermission_codename_and_more") in Migration.dependencies

    def test_migration_operations(self):
        """Test that migration has correct operations."""
        import importlib
        migration_module = importlib.import_module(
            'galaxy_ng.app.migrations.0059_delete_system_auditor_role_definition'
        )
        Migration = migration_module.Migration
        delete_system_auditor_role_definition = (
            migration_module.delete_system_auditor_role_definition
        )

        assert hasattr(Migration, 'operations')
        assert len(Migration.operations) == 1

        operation = Migration.operations[0]
        assert isinstance(operation, migrations.RunPython)

        # The RunPython operation should reference our function
        assert operation.code == delete_system_auditor_role_definition
        assert operation.reverse_code == migrations.RunPython.noop
