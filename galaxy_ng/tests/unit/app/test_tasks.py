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

from galaxy_ng.app.tasks import import_and_auto_approve, import_to_staging
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
        self.collection_version = CollectionVersion.objects.create(
            collection=collection,
            version='1.0.0',
        )
        self.collection_version.save()

        content_artifact = ContentArtifact.objects.create(
            artifact=self.artifact,
            content=self.collection_version,
        )
        content_artifact.save()

    @mock.patch('galaxy_ng.app.tasks.publishing.get_created_collection_versions')
    @mock.patch('galaxy_ng.app.tasks.publishing.general_create')
    @mock.patch('galaxy_ng.app.tasks.promotion.dispatch')
    @mock.patch('galaxy_ng.app.tasks.promotion.TaskGroup')
    def test_import_and_auto_approve(
        self, mocked_task_group, mocked_dispatch, mocked_create, mocked_get_created
    ):
        repo = AnsibleRepository.objects.get(name=staging_name)

        golden_repo = AnsibleRepository.objects.get(name=golden_name)

        mocked_get_created.return_value = [self.collection_version]

        import_and_auto_approve(
            '',  # username
            repo.pk,
            **{"general_args": ()}
        )

        self.assertTrue(mocked_create.call_count == 1)
        self.assertTrue(mocked_dispatch.call_count == 1)

        # test cannot find golden repo
        golden_repo.name = 'a_different_name_for_golden'
        golden_repo.save()
        mocked_get_created.side_effect = AnsibleDistribution.DoesNotExist
        with self.assertRaises(AnsibleDistribution.DoesNotExist):
            import_and_auto_approve(
                '',  # username
                repo.pk,
                **{"general_args": ()}
            )

    @mock.patch('galaxy_ng.app.tasks.publishing.get_created_collection_versions')
    @mock.patch('galaxy_ng.app.tasks.publishing.general_create')
    @mock.patch('galaxy_ng.app.tasks.promotion.dispatch')
    @mock.patch('galaxy_ng.app.tasks.promotion.TaskGroup')
    def test_import_to_staging(
        self, mocked_task_group, mocked_dispatch, mocked_create, mocked_get_created
    ):
        staging_repo = AnsibleRepository.objects.get(name=staging_name)

        repo_name = 'the_incoming_repo'
        repo = AnsibleRepository.objects.create(name=repo_name)
        dist = AnsibleDistribution(name=repo_name, base_path=repo_name)
        dist.repository = repo
        dist.save()

        mocked_get_created.return_value = [self.collection_version]

        import_to_staging(
            '',  # username
            **{"general_args": ()}
        )

        self.assertTrue(mocked_create.call_count == 1)
        self.assertTrue(mocked_dispatch.call_count == 1)

        # test cannot find staging repo
        staging_repo.name = 'a_different_name_for_staging'
        staging_repo.save()
        mocked_get_created.side_effect = AnsibleDistribution.DoesNotExist
        with self.assertRaises(AnsibleDistribution.DoesNotExist):
            import_to_staging(
                '',  # username
                **{"general_args": ()}
            )

    def test_log_collection_upload(self):
        with self.assertLogs(logger='automated_logging', level='INFO') as lm:
            _log_collection_upload('admin', 'namespace', 'name', '0.0.1')

            self.assertIn(
                "INFO:automated_logging:Collection uploaded by user 'admin': namespace-name-0.0.1",
                lm.output
            )
