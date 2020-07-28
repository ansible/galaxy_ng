import logging
import os
import tempfile
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings

from pulpcore.plugin.models import Artifact, PulpTemporaryFile, ContentArtifact
from pulp_ansible.app.models import (
    Collection, CollectionVersion, AnsibleRepository, AnsibleDistribution
)

from galaxy_ng.app.tasks import import_and_auto_approve, import_and_move_to_staging

log = logging.getLogger(__name__)

golden_name = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH
staging_name = settings.GALAXY_API_STAGING_DISTRIBUTION_BASE_PATH


@override_settings(WORKING_DIRECTORY=tempfile.mkdtemp(suffix='galaxy_ng_unittest'))
class TestTaskPublish(TestCase):
    # artifact_path = os.path.join(tempfile.gettempdir(), 'artifact-tmp')
    artifact_path = os.path.join(settings.WORKING_DIRECTORY, 'artifact-tmp')

    def setUp(self):
        with open(self.artifact_path, 'w') as f:
            f.write('Temp Artifact File')
        self.pulp_temp_file = PulpTemporaryFile.init_and_validate(self.artifact_path)
        self.pulp_temp_file.save()

        self.artifact = Artifact.from_pulp_temporary_file(self.pulp_temp_file)

        collection = Collection.objects.create(namespace='my_ns', name='my_name')
        self.collection_version = CollectionVersion.objects.create(collection=collection)
        self.collection_version.save()

        content_artifact = ContentArtifact.objects.create(
            artifact=self.artifact,
            content=self.collection_version,
        )
        content_artifact.save()

    @mock.patch('galaxy_ng.app.tasks.publishing.get_created_collection_versions')
    @mock.patch('galaxy_ng.app.tasks.publishing.import_collection')
    @mock.patch('galaxy_ng.app.tasks.publishing.enqueue_with_reservation')
    def test_import_and_auto_approve(self, mocked_enqueue, mocked_import, mocked_get_created):
        inbound_repo = AnsibleRepository.objects.create(name=staging_name)
        golden_repo = AnsibleRepository.objects.create(name=golden_name)

        golden_dist = AnsibleDistribution(name=golden_name, base_path=golden_name)
        staging_dist = AnsibleDistribution(name=staging_name, base_path=staging_name)
        golden_dist.repository = golden_repo
        staging_dist.repository = inbound_repo
        golden_dist.save()
        staging_dist.save()

        self.assertTrue(self.collection_version.certification == 'needs_review')

        mocked_get_created.return_value = [self.collection_version]

        import_and_auto_approve(self.pulp_temp_file.pk, repository_pk=inbound_repo.pk)

        self.collection_version.refresh_from_db()
        self.assertTrue(self.collection_version.certification == 'certified')
        self.assertTrue(mocked_import.call_count == 1)
        self.assertTrue(mocked_enqueue.call_count == 2)

        # test cannot find golden repo
        golden_repo.name = 'a_different_name_for_golden'
        golden_repo.save()
        mocked_get_created.side_effect = AnsibleDistribution.DoesNotExist
        with self.assertRaises(AnsibleDistribution.DoesNotExist):
            import_and_auto_approve(self.artifact.pk, repository_pk=inbound_repo.pk)

    @mock.patch('galaxy_ng.app.tasks.publishing.get_created_collection_versions')
    @mock.patch('galaxy_ng.app.tasks.publishing.import_collection')
    @mock.patch('galaxy_ng.app.tasks.publishing.enqueue_with_reservation')
    def test_import_and_move_to_staging(self, mocked_enqueue, mocked_import, mocked_get_created):
        inbound_name = 'the_incoming_repo'
        inbound_repo = AnsibleRepository.objects.create(name=inbound_name)
        staging_repo = AnsibleRepository.objects.create(name=staging_name)
        inbound_repo.save()
        staging_repo.save()

        inbound_dist = AnsibleDistribution(name=inbound_name, base_path=inbound_name)
        staging_dist = AnsibleDistribution(name=staging_name, base_path=staging_name)
        inbound_dist.repository = inbound_repo
        staging_dist.repository = staging_repo
        inbound_dist.save()
        staging_dist.save()

        mocked_get_created.return_value = [self.collection_version]

        import_and_move_to_staging(self.pulp_temp_file.pk, repository_pk=inbound_repo.pk)

        self.assertTrue(mocked_import.call_count == 1)
        self.assertTrue(mocked_enqueue.call_count == 2)

        # test cannot find staging repo
        staging_repo.name = 'a_different_name_for_staging'
        staging_repo.save()
        mocked_get_created.side_effect = AnsibleDistribution.DoesNotExist
        with self.assertRaises(AnsibleDistribution.DoesNotExist):
            import_and_move_to_staging(self.pulp_temp_file.pk, repository_pk=inbound_repo.pk)
