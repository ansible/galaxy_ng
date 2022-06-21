import logging
import os
import tempfile
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings
from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    Collection,
    CollectionVersion,
)
from pulpcore.plugin.models import Artifact, ContentArtifact, PulpTemporaryFile

from galaxy_ng.app.tasks import import_and_auto_approve, import_and_move_to_staging
from galaxy_ng.app.tasks.promotion import move_content
from galaxy_ng.app.tasks.publishing import _log_collection_upload

log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.DEBUG)

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

    def test_task_move_content(self):
        repo1 = AnsibleRepository.objects.get(name=staging_name)
        repo1_version_number = repo1.latest_version().number
        repo2 = AnsibleRepository.objects.get(name='rejected')
        repo2_version_number = repo2.latest_version().number

        self.assertNotIn(
            self.collection_version,
            CollectionVersion.objects.filter(pk__in=repo1.latest_version().content))
        self.assertNotIn(
            self.collection_version,
            CollectionVersion.objects.filter(pk__in=repo2.latest_version().content))

        qs = CollectionVersion.objects.filter(pk=self.collection_version.pk)
        with repo1.new_version() as new_version:
            new_version.add_content(qs)

        self.assertEqual(repo1_version_number + 1, repo1.latest_version().number)
        self.assertIn(
            self.collection_version,
            CollectionVersion.objects.filter(pk__in=repo1.latest_version().content))

        move_content(self.collection_version.pk, repo1.pk, repo2.pk)

        self.assertNotIn(
            self.collection_version,
            CollectionVersion.objects.filter(pk__in=repo1.latest_version().content))
        self.assertIn(
            self.collection_version,
            CollectionVersion.objects.filter(pk__in=repo2.latest_version().content))
        self.assertEqual(repo2_version_number + 1, repo2.latest_version().number)

    @mock.patch('galaxy_ng.app.tasks.publishing.get_created_collection_versions')
    @mock.patch('galaxy_ng.app.tasks.publishing.import_collection')
    @mock.patch('galaxy_ng.app.tasks.promotion.dispatch')
    def test_import_and_auto_approve(self, mocked_dispatch, mocked_import, mocked_get_created):
        inbound_repo = AnsibleRepository.objects.get(name=staging_name)

        golden_repo = AnsibleRepository.objects.get(name=golden_name)

        mocked_get_created.return_value = [self.collection_version]

        import_and_auto_approve(
            self.pulp_temp_file.pk,
            repository_pk=inbound_repo.pk,
            expected_namespace='',
            expected_name='',
            expected_version='',
            username='',
        )

        self.assertTrue(mocked_import.call_count == 1)
        self.assertTrue(mocked_dispatch.call_count == 1)

        # test cannot find golden repo
        golden_repo.name = 'a_different_name_for_golden'
        golden_repo.save()
        mocked_get_created.side_effect = AnsibleDistribution.DoesNotExist
        with self.assertRaises(AnsibleDistribution.DoesNotExist):
            import_and_auto_approve(
                self.artifact.pk,
                repository_pk=inbound_repo.pk,
                expected_namespace='',
                expected_name='',
                expected_version='',
                username='',
            )

    @mock.patch('galaxy_ng.app.tasks.publishing.get_created_collection_versions')
    @mock.patch('galaxy_ng.app.tasks.publishing.import_collection')
    @mock.patch('galaxy_ng.app.tasks.promotion.dispatch')
    def test_import_and_move_to_staging(self, mocked_dispatch, mocked_import, mocked_get_created):
        staging_repo = AnsibleRepository.objects.get(name=staging_name)

        inbound_name = 'the_incoming_repo'
        inbound_repo = AnsibleRepository.objects.create(name=inbound_name)
        inbound_dist = AnsibleDistribution(name=inbound_name, base_path=inbound_name)
        inbound_dist.repository = inbound_repo
        inbound_dist.save()

        mocked_get_created.return_value = [self.collection_version]

        import_and_move_to_staging(
            self.pulp_temp_file.pk,
            repository_pk=inbound_repo.pk,
            expected_namespace='',
            expected_name='',
            expected_version='',
            username='',
        )

        self.assertTrue(mocked_import.call_count == 1)
        self.assertTrue(mocked_dispatch.call_count == 1)

        # test cannot find staging repo
        staging_repo.name = 'a_different_name_for_staging'
        staging_repo.save()
        mocked_get_created.side_effect = AnsibleDistribution.DoesNotExist
        with self.assertRaises(AnsibleDistribution.DoesNotExist):
            import_and_move_to_staging(
                self.pulp_temp_file.pk,
                repository_pk=inbound_repo.pk,
                expected_namespace='',
                expected_name='',
                expected_version='',
                username='',
            )

    def test_log_collection_upload(self):
        with self.assertLogs(logger='automated_logging', level='INFO') as lm:
            _log_collection_upload('admin', 'namespace', 'name', '0.0.1')

            self.assertIn(
                "INFO:automated_logging:Collection uploaded by user 'admin': namespace-name-0.0.1",
                lm.output
            )
