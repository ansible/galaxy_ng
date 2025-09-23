import tempfile
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, mock_open

import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from pulpcore.plugin.models import Artifact

from galaxy_ng.app.tasks.namespaces import (
    dispatch_create_pulp_namespace_metadata,
    _download_avatar,
    _create_pulp_namespace,
    _add_namespace_metadata_to_repos,
    MAX_AVATAR_SIZE
)
from galaxy_ng.app.models import Namespace
from pulp_ansible.app.models import AnsibleNamespace


class TestDispatchCreatePulpNamespaceMetadata(TestCase):

    @patch('galaxy_ng.app.tasks.namespaces.dispatch')
    def test_dispatch_create_pulp_namespace_metadata(self, mock_dispatch):
        galaxy_ns = Mock(spec=Namespace)
        galaxy_ns.pk = 123
        download_logo = True

        dispatch_create_pulp_namespace_metadata(galaxy_ns, download_logo)

        mock_dispatch.assert_called_once_with(
            _create_pulp_namespace,
            kwargs={
                "galaxy_ns_pk": 123,
                "download_logo": True,
            }
        )


class TestDownloadAvatar(TestCase):

    def setUp(self):
        self.test_url = "https://example.com/avatar.png"
        self.namespace_name = "test_namespace"

    @patch('galaxy_ng.app.tasks.namespaces.asyncio.get_event_loop')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.ClientSession')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.TCPConnector')
    @patch('galaxy_ng.app.tasks.namespaces.HttpDownloader')
    @patch('galaxy_ng.app.tasks.namespaces.Artifact.objects.get')
    def test_download_avatar_existing_artifact(self, mock_artifact_get, mock_downloader_class,
                                               mock_connector, mock_session, mock_get_loop):
        # Setup mocks
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_downloader = Mock()
        mock_downloader.fetch.return_value = Mock(
            artifact_attributes={"size": 1024, "sha256": "test_sha256"}
        )
        mock_downloader_class.return_value = mock_downloader

        existing_artifact = Mock()
        mock_artifact_get.return_value = existing_artifact

        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop

        result = _download_avatar(self.test_url, self.namespace_name)

        self.assertEqual(result, existing_artifact)
        mock_artifact_get.assert_called_once_with(sha256="test_sha256")
        mock_loop.run_until_complete.assert_called_once_with(mock_session_instance.close())

    @patch('galaxy_ng.app.tasks.namespaces.asyncio.get_event_loop')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.ClientSession')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.TCPConnector')
    @patch('galaxy_ng.app.tasks.namespaces.HttpDownloader')
    def test_download_avatar_size_too_large(self, mock_downloader_class, mock_connector,
                                            mock_session, mock_get_loop):
        # Setup mocks
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_downloader = Mock()
        mock_downloader.fetch.return_value = Mock(
            artifact_attributes={"size": MAX_AVATAR_SIZE + 1}
        )
        mock_downloader_class.return_value = mock_downloader

        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop

        with pytest.raises(ValidationError) as exc_info:
            _download_avatar(self.test_url, self.namespace_name)

        assert "larger than" in str(exc_info.value)
        mock_loop.run_until_complete.assert_called_once_with(mock_session_instance.close())

    @patch('galaxy_ng.app.tasks.namespaces.asyncio.get_event_loop')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.ClientSession')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.TCPConnector')
    @patch('galaxy_ng.app.tasks.namespaces.HttpDownloader')
    def test_download_avatar_fetch_exception(self, mock_downloader_class, mock_connector,
                                             mock_session, mock_get_loop):
        # Setup mocks
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_downloader = Mock()
        mock_downloader.fetch.side_effect = Exception("Network error")
        mock_downloader_class.return_value = mock_downloader

        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop

        result = _download_avatar(self.test_url, self.namespace_name)

        self.assertIsNone(result)
        mock_loop.run_until_complete.assert_called_once_with(mock_session_instance.close())

    @patch('galaxy_ng.app.tasks.namespaces.asyncio.get_event_loop')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.ClientSession')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.TCPConnector')
    @patch('galaxy_ng.app.tasks.namespaces.HttpDownloader')
    @patch('galaxy_ng.app.tasks.namespaces.Artifact.objects.get')
    @patch('galaxy_ng.app.tasks.namespaces.PulpTemporaryUploadedFile.from_file')
    @patch('galaxy_ng.app.tasks.namespaces.ImageField')
    @patch('galaxy_ng.app.tasks.namespaces.Artifact.init_and_validate')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_avatar_create_new_artifact_valid_image(
        self, mock_open_file, mock_init_validate, mock_image_field, mock_temp_file,
        mock_artifact_get, mock_downloader_class, mock_connector, mock_session, mock_get_loop
    ):
        # Setup mocks
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_img = Mock()
        mock_img.artifact_attributes = {"size": 1024, "sha256": "test_sha256"}
        mock_img.path = "/tmp/test_image"

        mock_downloader = Mock()
        mock_downloader.fetch.return_value = mock_img
        mock_downloader_class.return_value = mock_downloader

        # Artifact doesn't exist
        mock_artifact_get.side_effect = Artifact.DoesNotExist

        mock_tf = Mock()
        mock_temp_file.return_value = mock_tf

        mock_image_field_instance = Mock()
        mock_image_field.return_value = mock_image_field_instance

        new_artifact = Mock()
        mock_init_validate.return_value = new_artifact

        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop

        result = _download_avatar(self.test_url, self.namespace_name)

        self.assertEqual(result, new_artifact)
        mock_image_field_instance.to_python.assert_called_once_with(mock_tf)
        new_artifact.save.assert_called_once()

    @patch('galaxy_ng.app.tasks.namespaces.asyncio.get_event_loop')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.ClientSession')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.TCPConnector')
    @patch('galaxy_ng.app.tasks.namespaces.HttpDownloader')
    @patch('galaxy_ng.app.tasks.namespaces.Artifact.objects.get')
    @patch('galaxy_ng.app.tasks.namespaces.PulpTemporaryUploadedFile.from_file')
    @patch('galaxy_ng.app.tasks.namespaces.ImageField')
    @patch('galaxy_ng.app.tasks.namespaces.ET.parse')
    @patch('galaxy_ng.app.tasks.namespaces.Artifact.init_and_validate')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_avatar_svg_image(
        self, mock_open_file, mock_init_validate, mock_et_parse, mock_image_field,
        mock_temp_file, mock_artifact_get, mock_downloader_class, mock_connector,
        mock_session, mock_get_loop
    ):
        # Setup mocks
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_img = Mock()
        mock_img.artifact_attributes = {"size": 1024, "sha256": "test_sha256"}
        mock_img.path = "/tmp/test_image"

        mock_downloader = Mock()
        mock_downloader.fetch.return_value = mock_img
        mock_downloader_class.return_value = mock_downloader

        # Artifact doesn't exist
        mock_artifact_get.side_effect = Artifact.DoesNotExist

        mock_tf = Mock()
        mock_temp_file.return_value = mock_tf

        # Image validation fails (not a PIL image)
        mock_image_field_instance = Mock()
        mock_image_field_instance.to_python.side_effect = ValidationError("Not an image")
        mock_image_field.return_value = mock_image_field_instance

        # But it's a valid SVG
        mock_root = Mock()
        mock_root.tag = '{http://www.w3.org/2000/svg}svg'
        mock_tree = Mock()
        mock_tree.find.return_value = mock_root
        mock_et_parse.return_value = mock_tree

        new_artifact = Mock()
        mock_init_validate.return_value = new_artifact

        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop

        result = _download_avatar(self.test_url, self.namespace_name)

        self.assertEqual(result, new_artifact)
        new_artifact.save.assert_called_once()

    @patch('galaxy_ng.app.tasks.namespaces.asyncio.get_event_loop')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.ClientSession')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.TCPConnector')
    @patch('galaxy_ng.app.tasks.namespaces.HttpDownloader')
    @patch('galaxy_ng.app.tasks.namespaces.Artifact.objects.get')
    @patch('galaxy_ng.app.tasks.namespaces.PulpTemporaryUploadedFile.from_file')
    @patch('galaxy_ng.app.tasks.namespaces.ImageField')
    @patch('galaxy_ng.app.tasks.namespaces.ET.parse')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_avatar_invalid_image(self, mock_open_file, mock_et_parse, mock_image_field,
                                           mock_temp_file, mock_artifact_get, mock_downloader_class,
                                           mock_connector, mock_session, mock_get_loop):
        # Setup mocks
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_img = Mock()
        mock_img.artifact_attributes = {"size": 1024, "sha256": "test_sha256"}
        mock_img.path = "/tmp/test_image"

        mock_downloader = Mock()
        mock_downloader.fetch.return_value = mock_img
        mock_downloader_class.return_value = mock_downloader

        # Artifact doesn't exist
        mock_artifact_get.side_effect = Artifact.DoesNotExist

        mock_tf = Mock()
        mock_temp_file.return_value = mock_tf

        # Image validation fails
        mock_image_field_instance = Mock()
        mock_image_field_instance.to_python.side_effect = ValidationError("Not an image")
        mock_image_field.return_value = mock_image_field_instance

        # And it's not a valid SVG either
        mock_root = Mock()
        mock_root.tag = 'not_svg'
        mock_tree = Mock()
        mock_tree.find.return_value = mock_root
        mock_et_parse.return_value = mock_tree

        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop

        with pytest.raises(ValidationError) as exc_info:
            _download_avatar(self.test_url, self.namespace_name)

        assert "is not a valid image" in str(exc_info.value)

    @patch('galaxy_ng.app.tasks.namespaces.asyncio.get_event_loop')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.ClientSession')
    @patch('galaxy_ng.app.tasks.namespaces.aiohttp.TCPConnector')
    @patch('galaxy_ng.app.tasks.namespaces.HttpDownloader')
    @patch('galaxy_ng.app.tasks.namespaces.Artifact.objects.get')
    @patch('galaxy_ng.app.tasks.namespaces.PulpTemporaryUploadedFile.from_file')
    @patch('galaxy_ng.app.tasks.namespaces.ImageField')
    @patch('galaxy_ng.app.tasks.namespaces.ET.parse')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_avatar_et_parse_error(self, mock_open_file, mock_et_parse,
                                            mock_image_field, mock_temp_file, mock_artifact_get,
                                            mock_downloader_class, mock_connector, mock_session,
                                            mock_get_loop):
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_img = Mock()
        mock_img.artifact_attributes = {"size": 1024, "sha256": "test_sha256"}
        mock_img.path = "/tmp/test_image"

        mock_downloader = Mock()
        mock_downloader.fetch.return_value = mock_img
        mock_downloader_class.return_value = mock_downloader

        mock_artifact_get.side_effect = Artifact.DoesNotExist

        mock_tf = Mock()
        mock_temp_file.return_value = mock_tf

        mock_image_field_instance = Mock()
        mock_image_field_instance.to_python.side_effect = ValidationError("Not an image")
        mock_image_field.return_value = mock_image_field_instance

        # ET.parse raises ParseError
        mock_et_parse.side_effect = ET.ParseError("Invalid XML")

        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop

        with pytest.raises(ValidationError) as exc_info:
            _download_avatar(self.test_url, self.namespace_name)

        assert "is not a valid image" in str(exc_info.value)


@override_settings(WORKING_DIRECTORY=tempfile.mkdtemp(suffix='galaxy_ng_unittest'))
class TestCreatePulpNamespace(TestCase):

    def setUp(self):
        self.galaxy_ns = Mock(spec=Namespace)
        self.galaxy_ns.pk = 123
        self.galaxy_ns.name = "test_namespace"
        self.galaxy_ns.company = "Test Company"
        self.galaxy_ns.email = "test@example.com"
        self.galaxy_ns.description = "Test description"
        self.galaxy_ns.resources = "test resources"
        self.galaxy_ns._avatar_url = "https://example.com/avatar.png"
        self.galaxy_ns.last_created_pulp_metadata = None
        self.galaxy_ns._state = Mock()

        # Mock links
        link1 = Mock()
        link1.name = "homepage"
        link1.url = "https://homepage.com"
        link2 = Mock()
        link2.name = "repository"
        link2.url = "https://github.com/test/repo"
        self.galaxy_ns.links.all.return_value = [link1, link2]

    @patch('galaxy_ng.app.tasks.namespaces.Namespace.objects.get')
    @patch('galaxy_ng.app.tasks.namespaces._download_avatar')
    @patch('galaxy_ng.app.tasks.namespaces.AnsibleNamespace.objects.get_or_create')
    @patch('galaxy_ng.app.tasks.namespaces.AnsibleNamespaceMetadata.objects.filter')
    @patch('galaxy_ng.app.tasks.namespaces.transaction.atomic')
    @patch('galaxy_ng.app.tasks.namespaces.ContentArtifact.objects.create')
    @patch('galaxy_ng.app.tasks.namespaces.RepositoryContent.objects.select_related')
    @patch('galaxy_ng.app.tasks.namespaces.dispatch')
    def test_create_pulp_namespace_new_metadata_with_avatar(
        self, mock_dispatch, mock_repo_content, mock_content_artifact_create, mock_atomic,
        mock_metadata_filter, mock_namespace_create, mock_download_avatar, mock_namespace_get
    ):
        mock_namespace_get.return_value = self.galaxy_ns

        avatar_artifact = Mock()
        avatar_artifact.sha256 = "avatar_sha256"
        mock_download_avatar.return_value = avatar_artifact

        ansible_namespace = Mock(spec=AnsibleNamespace)
        mock_namespace_create.return_value = (ansible_namespace, False)

        mock_metadata_filter.return_value.first.return_value = None

        repo_content = Mock()
        repo_content.repository = Mock()
        repo_content.repository.pk = 456
        mock_repo_content.return_value.order_by.return_value.filter.return_value.\
            distinct.return_value = [repo_content]

        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)

        with patch('galaxy_ng.app.tasks.namespaces.AnsibleNamespaceMetadata') as \
                mock_metadata_class:
            new_metadata = Mock()
            new_metadata.pk = 789
            new_metadata.name = "test_namespace"
            mock_metadata_class.return_value = new_metadata
            mock_metadata_class.objects = Mock()
            mock_metadata_class.objects.filter = mock_metadata_filter

            result = _create_pulp_namespace(123, True)

            mock_namespace_get.assert_called_once_with(pk=123)
            mock_download_avatar.assert_called_once_with(
                "https://example.com/avatar.png", "test_namespace"
            )

            expected_namespace_data = {
                "company": "Test Company",
                "email": "test@example.com",
                "description": "Test description",
                "resources": "test resources",
                "links": {
                    "homepage": "https://homepage.com",
                    "repository": "https://github.com/test/repo"
                },
                "avatar_sha256": "avatar_sha256",
                "name": "test_namespace",
            }
            mock_metadata_class.assert_called_once_with(
                namespace=ansible_namespace, **expected_namespace_data
            )

            new_metadata.calculate_metadata_sha256.assert_called_once()
            new_metadata.save.assert_called_once()
            self.assertEqual(self.galaxy_ns.last_created_pulp_metadata, new_metadata)
            self.galaxy_ns.save.assert_called_once()

            mock_content_artifact_create.assert_called_once_with(
                artifact=avatar_artifact,
                content=new_metadata,
                relative_path="test_namespace-avatar"
            )

            mock_dispatch.assert_called_once_with(
                _add_namespace_metadata_to_repos,
                kwargs={
                    "namespace_pk": 789,
                    "repo_list": [456],
                },
                exclusive_resources=[repo_content.repository]
            )

            self.assertIsNotNone(result)

    @patch('galaxy_ng.app.tasks.namespaces.Namespace.objects.get')
    @patch('galaxy_ng.app.tasks.namespaces._download_avatar')
    @patch('galaxy_ng.app.tasks.namespaces.AnsibleNamespace.objects.get_or_create')
    @patch('galaxy_ng.app.tasks.namespaces.AnsibleNamespaceMetadata.objects.filter')
    @patch('galaxy_ng.app.tasks.namespaces.transaction.atomic')
    @patch('galaxy_ng.app.tasks.namespaces.ContentArtifact.objects.create')
    @patch('galaxy_ng.app.tasks.namespaces.RepositoryContent.objects.select_related')
    @patch('galaxy_ng.app.tasks.namespaces.dispatch')
    def test_create_pulp_namespace_created_new_ansible_namespace(
        self, mock_dispatch, mock_repo_content, mock_content_artifact_create, mock_atomic,
        mock_metadata_filter, mock_namespace_create, mock_download_avatar, mock_namespace_get
    ):
        mock_namespace_get.return_value = self.galaxy_ns
        mock_download_avatar.return_value = None

        ansible_namespace = Mock(spec=AnsibleNamespace)
        mock_namespace_create.return_value = (ansible_namespace, True)  # created=True

        mock_metadata_filter.return_value.first.return_value = None
        mock_repo_content.return_value.order_by.return_value.filter.return_value.\
            distinct.return_value = []

        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)

        with patch('galaxy_ng.app.tasks.namespaces.AnsibleNamespaceMetadata') as \
                mock_metadata_class:
            new_metadata = Mock()
            new_metadata.pk = 789
            new_metadata.name = "test_namespace"
            mock_metadata_class.return_value = new_metadata
            mock_metadata_class.objects = Mock()
            mock_metadata_class.objects.filter = mock_metadata_filter

            _create_pulp_namespace(123, False)

            mock_namespace_create.assert_called_once_with(name="test_namespace")
            new_metadata.save.assert_called_once()


class TestAddNamespaceMetadataToRepos(TestCase):

    @patch('galaxy_ng.app.tasks.namespaces.add_and_remove')
    def test_add_namespace_metadata_to_repos(self, mock_add_and_remove):
        namespace_pk = 123
        repo_list = [456, 789, 101112]

        _add_namespace_metadata_to_repos(namespace_pk, repo_list)

        # Should call add_and_remove for each repo
        expected_calls = [
            ((456,), {'add_content_units': [123], 'remove_content_units': []}),
            ((789,), {'add_content_units': [123], 'remove_content_units': []}),
            ((101112,), {'add_content_units': [123], 'remove_content_units': []}),
        ]

        self.assertEqual(mock_add_and_remove.call_count, 3)
        for i, call in enumerate(mock_add_and_remove.call_args_list):
            self.assertEqual(call.args, expected_calls[i][0])
            self.assertEqual(call.kwargs, expected_calls[i][1])

    @patch('galaxy_ng.app.tasks.namespaces.add_and_remove')
    def test_add_namespace_metadata_to_repos_empty_list(self, mock_add_and_remove):
        namespace_pk = 123
        repo_list = []

        _add_namespace_metadata_to_repos(namespace_pk, repo_list)

        mock_add_and_remove.assert_not_called()
