from importlib import import_module

from django.db import connection
from django.test import TestCase
from django.apps import apps

from pulp_ansible.app.models import CollectionRemote


class TestRemoteRHCertifiedCollectionURL(TestCase):

    def _run_migration(self):
        migration = import_module("galaxy_ng.app.migrations.0030_update_collection_remote_rhcertified_url")
        migration.update_collection_remote_rhcertified_url(apps, connection.schema_editor())
    
    def test_correct_url_update_after_migration(self):
        url = 'https://cloud.redhat.com/api/automation-hub/content/1237261-synclist/'
        CollectionRemote.objects.filter(name="rh-certified").update(url=url)        
        
        remote = CollectionRemote.objects.get(name='rh-certified')
        self.assertEqual(remote.url, url)

        self._run_migration()
        
        remote.refresh_from_db()
        self.assertEqual(remote.url, 'https://console.redhat.com/api/automation-hub/content/1237261-synclist/')

    def test_no_url_change_after_migration(self):
        url = 'https://console.stage.redhat.com/api/automation-hub/'
        CollectionRemote.objects.filter(name="rh-certified").update(url=url)

        remote = CollectionRemote.objects.get(name='rh-certified')
        self.assertEqual(remote.url, url)

        self._run_migration()

        remote.refresh_from_db()
        self.assertEqual(remote.url, url)
