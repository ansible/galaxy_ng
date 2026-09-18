from io import StringIO
from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase
from rest_framework import serializers

from galaxy_ng.app.api.v3.serializers.execution_environment import (
    ContainerManifestDetailSerializer,
    ContainerManifestSerializer,
    ContainerNamespaceSerializer,
    ContainerRepositorySerializer,
    ContainerRepositoryHistorySerializer,
    ManifestListManifestSerializer,
)


class TestContainerRepositorySerializer(SimpleTestCase):
    def test_retention_field_accepts_value_and_null(self):
        serializer = ContainerRepositorySerializer(
            data={"retain_repo_versions": 5}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data, {"repository": {"retain_repo_versions": 5}}
        )

        serializer = ContainerRepositorySerializer(
            data={"retain_repo_versions": 0}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data, {"repository": {"retain_repo_versions": 0}}
        )

        serializer = ContainerRepositorySerializer(
            data={"retain_repo_versions": None}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data, {"repository": {"retain_repo_versions": None}}
        )

        serializer = ContainerRepositorySerializer(
            data={"retain_repo_versions": -1}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("retain_repo_versions", serializer.errors)

    def test_update_sets_repository_retention(self):
        instance = Mock()
        instance.repository = Mock()
        serializer = ContainerRepositorySerializer()

        with patch.object(
            serializers.ModelSerializer, "update", return_value=instance
        ) as update:
            result = serializer.update(
                instance, {"repository": {"retain_repo_versions": 5}}
            )

        self.assertIs(result, instance)
        self.assertEqual(instance.repository.retain_repo_versions, 5)
        instance.repository.save.assert_called_once_with(
            update_fields=("retain_repo_versions",)
        )
        update.assert_called_once_with(instance, {})

    def test_update_without_retention_only_saves_distribution(self):
        instance = Mock()
        instance.repository = Mock()
        serializer = ContainerRepositorySerializer()

        with patch.object(
            serializers.ModelSerializer, "update", return_value=instance
        ) as update:
            serializer.update(instance, {})

        instance.repository.save.assert_not_called()
        update.assert_called_once_with(instance, {})

    def test_serializer_methods(self):
        repository = Mock(
            pk="repository-id",
            pulp_type="container.container",
            name="repo",
            description="description",
            pulp_created="created",
            pulp_last_updated="updated",
            pulp_labels={"label": "value"},
            remote=None,
        )
        repository.latest_version.return_value.number = 4
        repository.content.filter.return_value.count.return_value = 0
        distribution = Mock(
            pk="distribution-id",
            name="distribution",
            pulp_created="created",
            pulp_last_updated="updated",
            base_path="namespace/repo",
            pulp_labels={},
            repository=repository,
            namespace=Mock(),
        )
        distribution.namespace.name = "namespace"
        serializer = ContainerRepositorySerializer()

        self.assertEqual(serializer.get_namespace(distribution), "namespace")
        self.assertEqual(serializer.get_id(distribution), "distribution-id")
        self.assertEqual(serializer.get_created_at(distribution), "created")
        self.assertEqual(serializer.get_updated_at(distribution), "updated")
        self.assertEqual(serializer.get_pulp(distribution)["repository"]["sign_state"], "unsigned")

    @patch(
        "galaxy_ng.app.api.v3.serializers.execution_environment."
        "ui_serializers.ContainerRemoteSerializer"
    )
    def test_get_pulp_with_remote_and_signature(self, remote_serializer):
        remote = Mock()
        remote.cast.return_value = "cast-remote"
        remote_serializer.return_value.data = {"name": "remote"}
        repository = Mock(remote=remote)
        repository.content.filter.return_value.count.return_value = 1
        distribution = Mock(repository=repository)

        result = ContainerRepositorySerializer().get_pulp(distribution)

        remote_serializer.assert_called_once_with("cast-remote", context={})
        self.assertEqual(result["repository"]["remote"], {"name": "remote"})
        self.assertEqual(result["repository"]["sign_state"], "signed")


class TestExecutionEnvironmentSerializerMethods(SimpleTestCase):
    def test_manifest_list_digest_and_namespace_owners(self):
        self.assertEqual(
            ManifestListManifestSerializer().get_digest(Mock(manifest_list=Mock(digest="sha256:1"))),
            "sha256:1",
        )

        with patch(
            "galaxy_ng.app.api.v3.serializers.execution_environment.get_users_with_perms"
        ) as get_users:
            get_users.return_value.values_list.return_value = ["alice"]
            result = ContainerNamespaceSerializer().get_owners(Mock())

        self.assertEqual(result, ["alice"])
        get_users.assert_called_once_with(
            get_users.call_args.args[0], with_group_users=False, for_concrete_model=True
        )

    def test_manifest_serializer_methods(self):
        serializer = ContainerManifestSerializer()
        blob = Mock(digest="sha256:blob", artifact_list=[Mock(size=12)])
        empty_blob = Mock(artifact_list=[])
        manifest = Mock(
            blob_list=[blob, empty_blob],
            config_blob=Mock(digest="sha256:config"),
        )
        latest_tag = Mock()
        latest_tag.name = "latest"
        stable_tag = Mock()
        stable_tag.name = "stable"
        manifest.tagged_manifests.all.return_value = [latest_tag, stable_tag]

        self.assertEqual(serializer.get_layers(manifest), [{"digest": "sha256:blob", "size": 12}])
        self.assertEqual(serializer.get_config_blob(manifest), {"digest": "sha256:config"})
        self.assertEqual(serializer.get_tags(manifest), ["latest", "stable"])

        manifest.config_blob = None
        self.assertEqual(serializer.get_config_blob(manifest), {})

    def test_manifest_detail_config_blob(self):
        artifact = MagicMock()
        artifact.file.open.return_value.__enter__.return_value = StringIO('{"key": "value"}')
        manifest = Mock(config_blob=Mock(digest="sha256:config"))
        manifest.config_blob._artifacts.first.return_value = artifact

        result = ContainerManifestDetailSerializer().get_config_blob(manifest)

        self.assertEqual(
            result, {"digest": "sha256:config", "data": {"key": "value"}}
        )

    @patch("galaxy_ng.app.api.v3.serializers.execution_environment.container_models.Tag")
    @patch("galaxy_ng.app.api.v3.serializers.execution_environment.container_models.Manifest")
    def test_repository_history_content_info(self, manifest_model, tag_model):
        serializer = ContainerRepositoryHistorySerializer()
        manifest_model.objects.get.return_value = Mock(digest="sha256:manifest")
        tag = Mock(tagged_manifest=Mock(digest="sha256:tag"))
        tag.name = "latest"
        tag_model.objects.select_related.return_value.get.return_value = tag

        self.assertEqual(
            serializer._content_info(Mock(pk="other", pulp_type="other")),
            {"pulp_id": "other", "pulp_type": "other", "manifest_digest": None, "tag_name": None},
        )
        self.assertEqual(
            serializer._content_info(Mock(pk="manifest", pulp_type="container.manifest")),
            {
                "pulp_id": "manifest",
                "pulp_type": "container.manifest",
                "manifest_digest": "sha256:manifest",
                "tag_name": None,
            },
        )
        self.assertEqual(
            serializer._content_info(Mock(pk="tag", pulp_type="container.tag")),
            {
                "pulp_id": "tag",
                "pulp_type": "container.tag",
                "manifest_digest": "sha256:tag",
                "tag_name": "latest",
            },
        )

    def test_repository_history_added_and_removed(self):
        serializer = ContainerRepositoryHistorySerializer()
        serializer._content_info = Mock(side_effect=lambda content: content.pk)
        repository_version = Mock()
        repository_version.added_memberships.all.return_value = [Mock(content=Mock(pk="added"))]
        repository_version.removed_memberships.all.return_value = [Mock(content=Mock(pk="removed"))]

        self.assertEqual(serializer.get_added(repository_version), ["added"])
        self.assertEqual(serializer.get_removed(repository_version), ["removed"])
