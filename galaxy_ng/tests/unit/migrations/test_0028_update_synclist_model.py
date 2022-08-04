from importlib import import_module

from django.db import connection
from django.test import TestCase
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository
from django.apps import apps

from galaxy_ng.app.models import SyncList

"""
Test migration custom Python in RunPython operation.

This pattern does not test the schema edits that exist in the migration.

This is not tested in a historical context, but uses latest models.
"""


class TestEditSyncListObj(TestCase):
    def _run_python_operation(self):
        """Calls RunPython operation, passes schema_editor"""
        migration = import_module("galaxy_ng.app.migrations.0028_update_synclist_model")
        migration.populate_synclist_distros(apps, connection.schema_editor())

    def test_match_synclist_to_distro(self):
        # Setup data, SyncList and Distribution with matching names
        repository = AnsibleRepository.objects.get(name="published")
        synclist_name = "33557799-synclist"
        synclist = SyncList.objects.create(
            name=synclist_name, repository=repository, upstream_repository=repository
        )
        distribution = AnsibleDistribution.objects.create(
            name=synclist_name,
            base_path=synclist_name,
            repository=repository,
            pulp_type=repository.pulp_type,
        )

        # Check that SyncList has empty distribution field
        self.assertIsNone(synclist.distribution)

        self._run_python_operation()

        # Check that SyncList has populated distribution field
        synclist.refresh_from_db()
        self.assertEqual(synclist.distribution, distribution)

    def test_synclist_no_matching_distro(self):
        # Setup data, SyncList with no matching Distribution
        synclist = SyncList.objects.create(
            name="99775533-synclist", repository=None, upstream_repository=None
        )

        # Check that SyncList has empty distribution field
        self.assertIsNone(synclist.distribution)

        self._run_python_operation()

        # Check that SyncList has not changed
        synclist_after_operation = SyncList.objects.get(pk=synclist.pk)
        self.assertEqual(synclist, synclist_after_operation)
