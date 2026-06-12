import json
import tempfile
from importlib import import_module

from django.apps import apps
from django.db import migrations
from django.db.models import Q
from django.test import TestCase

from pulp_container.app.models import Manifest
from pulp_container.constants import MEDIA_TYPE
from pulpcore.plugin.models import Artifact, ContentArtifact


migration_module = import_module(
    "galaxy_ng.app.migrations.0060_handle_container_image_data"
)


class TestHandleContainerImageDataMigration(TestCase):
    """Test migration 0060_handle_container_image_data.

    This migration backfills the Manifest.data database field that was added
    in pulp_container 2.20.0 (migration 0039). The field was added as nullable,
    and existing manifests were left with data=None. The backfill reads the
    manifest JSON from each manifest's backing artifact file and copies it
    into the data column.

    The migration must handle several scenarios:
    - Manifests with data=None and a backing artifact (the common case, fixable)
    - Manifests with data=None and NO backing artifact (e.g. artifact was removed
      by Pulp's reclaim space feature; these are skipped gracefully)
    - Manifests that already have data populated (skipped)
    - Fresh installs with no manifests at all (no-op)
    """

    def test_migration_dependencies(self):
        """Verify the migration depends on both the galaxy and container app
        chains. Needed because the migration writes to the container
        Manifest model, which must have the data column before we run."""
        Migration = migration_module.Migration
        assert ("galaxy", "0059_delete_system_auditor_role_definition") in Migration.dependencies
        assert (
            "container", "0045_alter_manifest_compressed_image_size"
        ) in Migration.dependencies

    def test_migration_operations(self):
        """Verify the migration has exactly one RunPython operation pointing
        to handle_image_data, with a noop reverse since the data population
        cannot be meaningfully undone."""
        Migration = migration_module.Migration
        assert len(Migration.operations) == 1
        operation = Migration.operations[0]
        assert isinstance(operation, migrations.RunPython)
        assert operation.code == migration_module.handle_image_data
        assert operation.reverse_code == migrations.RunPython.noop
        assert operation.elidable is True

    def test_handle_image_data_runs_with_no_manifests(self):
        """Run the migration when no manifests exist. Needed to confirm
        the migration doesn't error on fresh installs where there is
        nothing to backfill."""
        migration_module.handle_image_data(apps, None)

    def _create_manifest_with_artifact(self, digest_char, manifest_json):
        """Helper to create a Manifest with an associated Artifact containing manifest JSON."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write(manifest_json)
            temp_path = f.name

        artifact = Artifact.init_and_validate(temp_path)
        artifact.save()

        manifest = Manifest(
            digest="sha256:" + digest_char * 64,
            schema_version=2,
            media_type=MEDIA_TYPE.MANIFEST_V2,
            data=None,
            type=None,
            architecture=None,
            os=None,
            compressed_image_size=None,
        )
        manifest.save()

        ContentArtifact.objects.create(
            artifact=artifact,
            content=manifest,
            relative_path="manifest.json",
        )

        return manifest

    def test_migration_populates_manifest_data(self):
        """Create a manifest with data=None and a backing artifact, then
        run the migration. Verify it reads the artifact, populates the
        data field with the manifest JSON, and fills in metadata like
        compressed_image_size. This simulates a manifest that existed
        before the pulp_container upgrade and never had its data field
        backfilled."""
        manifest_json = json.dumps({
            "schemaVersion": 2,
            "mediaType": MEDIA_TYPE.MANIFEST_V2,
            "config": {
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "digest": "sha256:" + "c" * 64,
                "size": 100,
            },
            "layers": [
                {
                    "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                    "digest": "sha256:" + "d" * 64,
                    "size": 2048,
                },
                {
                    "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                    "digest": "sha256:" + "e" * 64,
                    "size": 4096,
                },
            ],
        })

        manifest = self._create_manifest_with_artifact("a", manifest_json)

        try:
            assert manifest.data is None
            assert manifest.type is None
            assert manifest.compressed_image_size is None

            migration_module.handle_image_data(apps, None)

            manifest.refresh_from_db()
            assert manifest.data is not None
            assert manifest.data == manifest_json
            assert manifest.type is not None
            assert manifest.compressed_image_size == 2048 + 4096
        finally:
            ContentArtifact.objects.filter(content=manifest).delete()
            manifest.delete()

    def test_migration_skips_already_populated_manifests(self):
        """Create a manifest with all fields already populated and run the
        migration. Verify none of the fields are modified. Needed to
        confirm the migration only touches manifests that need fixing."""
        manifest = Manifest(
            digest="sha256:" + "b" * 64,
            schema_version=2,
            media_type=MEDIA_TYPE.MANIFEST_V2,
            data='{"schemaVersion": 2}',
            type="image",
            architecture="amd64",
            os="linux",
            compressed_image_size=1024,
            annotations={"key": "value"},
            labels={"key": "value"},
        )
        manifest.save()

        try:
            migration_module.handle_image_data(apps, None)

            manifest.refresh_from_db()
            assert manifest.data == '{"schemaVersion": 2}'
            assert manifest.type == "image"
            assert manifest.architecture == "amd64"
            assert manifest.os == "linux"
            assert manifest.compressed_image_size == 1024
        finally:
            manifest.delete()

    def test_manifests_with_null_fields_are_detected(self):
        """Create a manifest with null metadata fields and verify the
        query used by the migration finds it. Needed to confirm the
        detection logic correctly identifies manifests that need fixing."""
        manifest = Manifest(
            digest="sha256:" + "f" * 64,
            schema_version=2,
            media_type=MEDIA_TYPE.MANIFEST_V2,
            data=None,
            type=None,
            architecture=None,
            os=None,
            compressed_image_size=None,
        )
        manifest.save()

        try:
            qs = Manifest.objects.filter(
                Q(data__isnull=True)
                | Q(type__isnull=True)
                | Q(architecture__isnull=True)
                | Q(os__isnull=True)
                | Q(compressed_image_size__isnull=True)
            ).exclude(
                media_type__in=[
                    MEDIA_TYPE.MANIFEST_LIST,
                    MEDIA_TYPE.INDEX_OCI,
                    MEDIA_TYPE.MANIFEST_V1,
                ]
            )
            assert qs.filter(pk=manifest.pk).exists()
        finally:
            manifest.delete()

    def test_migration_handles_missing_artifacts(self):
        """Create a manifest with data=None and NO backing artifact, then
        run the migration. Verify it completes without crashing and the
        manifest's data remains None. This can happen when Pulp's reclaim
        space feature has removed the artifact file to free disk. The
        migration must skip these gracefully rather than failing the
        entire upgrade."""
        manifest = Manifest(
            digest="sha256:" + "9" * 64,
            schema_version=2,
            media_type=MEDIA_TYPE.MANIFEST_V2,
            data=None,
            type=None,
            architecture=None,
            os=None,
            compressed_image_size=None,
        )
        manifest.save()

        try:
            migration_module.handle_image_data(apps, None)

            manifest.refresh_from_db()
            assert manifest.data is None
        finally:
            manifest.delete()

    def test_migration_is_idempotent(self):
        """Run the migration twice on the same manifest. Verify the second
        run completes without errors and doesn't corrupt data. The first
        run copies artifact data into the data field and then clears the
        artifact association. The second run encounters a manifest with
        data already populated and no artifact, and must handle both
        conditions without failing."""
        manifest_json = json.dumps({
            "schemaVersion": 2,
            "mediaType": MEDIA_TYPE.MANIFEST_V2,
            "config": {
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "digest": "sha256:" + "c" * 64,
                "size": 100,
            },
            "layers": [
                {
                    "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                    "digest": "sha256:" + "d" * 64,
                    "size": 1024,
                },
            ],
        })

        manifest = self._create_manifest_with_artifact("8", manifest_json)

        try:
            migration_module.handle_image_data(apps, None)

            manifest.refresh_from_db()
            assert manifest.data is not None

            migration_module.handle_image_data(apps, None)

            manifest.refresh_from_db()
            assert manifest.data == manifest_json
        finally:
            ContentArtifact.objects.filter(content=manifest).delete()
            manifest.delete()

    def test_manifests_with_populated_fields_are_skipped(self):
        """Create a manifest with all fields populated and verify the
        detection query does NOT find it. Needed to confirm the query
        only matches manifests that actually need backfilling."""
        manifest = Manifest(
            digest="sha256:" + "0" * 64,
            schema_version=2,
            media_type=MEDIA_TYPE.MANIFEST_V2,
            data='{"schemaVersion": 2}',
            type="image",
            architecture="amd64",
            os="linux",
            compressed_image_size=1024,
            annotations={"key": "value"},
            labels={"key": "value"},
        )
        manifest.save()

        try:
            qs = Manifest.objects.filter(
                Q(data__isnull=True)
                | Q(type__isnull=True)
                | Q(architecture__isnull=True)
                | Q(os__isnull=True)
                | Q(compressed_image_size__isnull=True)
            ).exclude(
                media_type__in=[
                    MEDIA_TYPE.MANIFEST_LIST,
                    MEDIA_TYPE.INDEX_OCI,
                    MEDIA_TYPE.MANIFEST_V1,
                ]
            )
            assert not qs.filter(pk=manifest.pk).exists()
        finally:
            manifest.delete()
