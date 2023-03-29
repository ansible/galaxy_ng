import logging
import os
import tempfile

from django.conf import settings
from django.test import TestCase, override_settings
from pulp_ansible.app.models import (
    Collection,
    CollectionVersion,
)
from pulpcore.plugin.models import Artifact, ContentArtifact, PulpTemporaryFile

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

    def test_log_collection_upload(self):
        with self.assertLogs(logger='automated_logging', level='INFO') as lm:
            _log_collection_upload('admin', 'namespace', 'name', '0.0.1')

            self.assertIn(
                "INFO:automated_logging:Collection uploaded by user 'admin': namespace-name-0.0.1",
                lm.output
            )
