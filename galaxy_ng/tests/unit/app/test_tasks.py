import logging
import os
import tempfile
from unittest import mock

from django.test import TestCase
from pulpcore.plugin.models import Artifact, ContentArtifact
from pulp_ansible.app.models import Collection, CollectionVersion

from galaxy_ng.app.tasks import import_and_auto_approve

log = logging.getLogger(__name__)


class TestTaskImportAndAutoApprove(TestCase):
    artifact_path = os.path.join(tempfile.gettempdir(), 'artifact-tmp')

    def setUp(self):
        with open(self.artifact_path, 'w') as f:
            f.write('Temp Artifact File')
        self.artifact = Artifact.init_and_validate(self.artifact_path)
        self.artifact.save()

        collection = Collection.objects.create(namespace='my_ns', name='my_name')
        self.collection_version = CollectionVersion.objects.create(collection=collection)
        self.collection_version.save()

        content_artifact = ContentArtifact.objects.create(
            artifact=self.artifact,
            content=self.collection_version,
        )
        content_artifact.save()

    @mock.patch('galaxy_ng.app.tasks.publishing.import_collection')
    def test_import_and_auto_approve(self, mocked_import_collection):
        self.assertTrue(self.collection_version.certification == 'needs_review')
        import_and_auto_approve(self.artifact.pk)
        self.collection_version.refresh_from_db()
        self.assertTrue(self.collection_version.certification == 'certified')
