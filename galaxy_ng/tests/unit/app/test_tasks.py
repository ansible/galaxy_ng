import logging
import os
import tempfile
from unittest import mock

from django.test import TestCase
from pulpcore.plugin.models import Artifact, ContentArtifact
from pulp_ansible.app.models import Collection, CollectionVersion, AnsibleRepository

from galaxy_ng.app.tasks import import_and_auto_approve, import_and_move_to_staging

log = logging.getLogger(__name__)


class TestTaskPublish(TestCase):
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

    @mock.patch('galaxy_ng.app.tasks.publishing.import_collection')
    @mock.patch('galaxy_ng.app.tasks.publishing.enqueue_with_reservation')
    def test_import_and_move_to_staging(self, mocked_enqueue, mocked_import):
        inbound_repo = AnsibleRepository.objects.create(name='the_incoming_repo')
        staging_repo = AnsibleRepository.objects.create(name='staging')
        import_and_move_to_staging(self.artifact.pk, repository_pk=inbound_repo.pk)
        self.assertTrue(mocked_import.call_count == 1)
        self.assertTrue(mocked_enqueue.call_count == 2)

        # test cannot find staging repo
        staging_repo.name = 'a_different_name_for_staging'
        staging_repo.save()
        staging_errmsg = 'Could not find staging repository: "staging"'
        with self.assertRaisesMessage(RuntimeError, staging_errmsg):
            import_and_move_to_staging(self.artifact.pk, repository_pk=inbound_repo.pk)
