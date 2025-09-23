from unittest.mock import Mock, patch, mock_open
from urllib.parse import urlencode, quote

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.http.request import HttpRequest
from django.test import TestCase

from galaxy_ng.app.tasks.index_registry import (
    CouldNotCreateContainerError,
    _get_request,
    _parse_catalog_repositories,
    _update_distro_readme_and_description,
    create_or_update_remote_container,
    index_execution_environments_from_redhat_registry,
    CATALOG_API
)


class TestCouldNotCreateContainerError(TestCase):

    def test_error_message_without_error(self):
        error = CouldNotCreateContainerError("test-container")
        self.assertIn("test-container", str(error.message))

    def test_error_message_with_error(self):
        error = CouldNotCreateContainerError("test-container", "Some error occurred")
        self.assertIn("test-container", str(error.message))
        self.assertIn("Some error occurred", str(error.message))


class TestGetRequest(TestCase):

    def test_get_request_empty_data(self):
        result = _get_request({})
        self.assertIsInstance(result, HttpRequest)

    def test_get_request_with_multiple_attributes(self):
        request_data = {
            'method': 'POST',
            'path': '/api/test/',
            'user': Mock(),
            'META': {'HTTP_AUTHORIZATION': 'Bearer token'},
            'content_type': 'application/json'
        }

        result = _get_request(request_data)

        self.assertEqual(result.method, 'POST')
        self.assertEqual(result.path, '/api/test/')
        self.assertEqual(result.META, request_data['META'])
        self.assertEqual(result.content_type, 'application/json')


class TestParseCatalogRepositories(TestCase):

    def test_parse_catalog_repositories_basic(self):
        response_data = {
            'data': [
                {
                    'repository': 'test-container-1',
                    'display_data': {
                        'short_description': 'Test container 1',
                        'long_description_markdown': '# Test Container 1\nA test container'
                    }
                },
                {
                    'repository': 'test-container-2',
                    'display_data': {
                        'short_description': 'Test container 2',
                        'long_description_markdown': '# Test Container 2\nAnother test container'
                    }
                }
            ]
        }

        result = _parse_catalog_repositories(response_data)

        self.assertEqual(len(result), 2)

        self.assertEqual(result[0]['name'], 'test-container-1')
        self.assertEqual(result[0]['upstream_name'], 'test-container-1')
        self.assertEqual(result[0]['description'], 'Test container 1')
        self.assertEqual(result[0]['readme'], '# Test Container 1\nA test container')

        self.assertEqual(result[1]['name'], 'test-container-2')
        self.assertEqual(result[1]['upstream_name'], 'test-container-2')
        self.assertEqual(result[1]['description'], 'Test container 2')
        self.assertEqual(result[1]['readme'], '# Test Container 2\nAnother test container')

    def test_parse_catalog_repositories_empty_data(self):
        response_data = {'data': []}
        result = _parse_catalog_repositories(response_data)
        self.assertEqual(result, [])

    def test_parse_catalog_repositories_minimal_data(self):
        response_data = {
            'data': [
                {
                    'repository': 'minimal-container',
                    'display_data': {
                        'short_description': '',
                        'long_description_markdown': ''
                    }
                }
            ]
        }

        result = _parse_catalog_repositories(response_data)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'minimal-container')
        self.assertEqual(result[0]['description'], '')
        self.assertEqual(result[0]['readme'], '')


class TestUpdateDistroReadmeAndDescription(TestCase):

    def setUp(self):
        self.distro = Mock()
        self.readme_mock = Mock()
        self.container_data = {
            'readme': '# Test Readme\nThis is a test readme',
            'description': 'Test description'
        }

    @patch('galaxy_ng.app.tasks.index_registry.models.ContainerDistroReadme.objects.get_or_create')
    def test_update_distro_readme_and_description(self, mock_get_or_create):
        mock_get_or_create.return_value = (self.readme_mock, False)

        _update_distro_readme_and_description(self.distro, self.container_data)

        mock_get_or_create.assert_called_once_with(container=self.distro)
        self.assertEqual(self.readme_mock.text, self.container_data['readme'])
        self.readme_mock.save.assert_called_once()
        self.assertEqual(self.distro.description, self.container_data['description'])
        self.distro.save.assert_called_once()

    @patch('galaxy_ng.app.tasks.index_registry.models.ContainerDistroReadme.objects.get_or_create')
    def test_update_distro_readme_and_description_created_new(self, mock_get_or_create):
        mock_get_or_create.return_value = (self.readme_mock, True)

        _update_distro_readme_and_description(self.distro, self.container_data)

        mock_get_or_create.assert_called_once_with(container=self.distro)
        self.assertEqual(self.readme_mock.text, self.container_data['readme'])
        self.readme_mock.save.assert_called_once()

    @patch('galaxy_ng.app.tasks.index_registry.models.ContainerDistroReadme.objects.get_or_create')
    def test_update_distro_readme_and_description_empty_data(self, mock_get_or_create):
        mock_get_or_create.return_value = (self.readme_mock, False)
        container_data = {'readme': '', 'description': ''}

        _update_distro_readme_and_description(self.distro, container_data)

        self.assertEqual(self.readme_mock.text, '')
        self.assertEqual(self.distro.description, '')


class TestCreateOrUpdateRemoteContainer(TestCase):

    def setUp(self):
        self.container_data = {
            'name': 'test-container',
            'description': 'Test description',
            'readme': 'Test readme'
        }
        self.registry_pk = 123
        self.request_data = {'user': Mock(), 'method': 'POST'}

        self.distro = Mock()
        self.repo = Mock()
        self.remote = Mock()
        self.remote_registry = Mock()
        self.remote_registry.pk = self.registry_pk

    @patch('galaxy_ng.app.tasks.index_registry.container_models.ContainerDistribution.objects.get')
    @patch('galaxy_ng.app.tasks.index_registry._update_distro_readme_and_description')
    @patch('galaxy_ng.app.tasks.index_registry.models.ContainerRegistryRepos.objects.get')
    @patch('galaxy_ng.app.tasks.index_registry.container_models.ContainerRepository.get_pulp_type')
    def test_update_existing_remote_container(self, mock_get_pulp_type, mock_registry_repos_get,
                                              mock_update_distro, mock_distro_get):
        # Setup existing remote container
        mock_get_pulp_type.return_value = 'container.container'
        self.repo.pulp_type = 'container.container'
        self.repo.remote = self.remote
        self.distro.repository = self.repo
        mock_distro_get.return_value = self.distro

        registry_repo = Mock()
        registry_repo.registry = self.remote_registry
        mock_registry_repos_get.return_value = registry_repo

        create_or_update_remote_container(self.container_data, self.registry_pk, self.request_data)

        mock_distro_get.assert_called_once_with(base_path='test-container')
        mock_registry_repos_get.assert_called_once_with(repository_remote=self.remote)
        mock_update_distro.assert_called_once_with(self.distro, self.container_data)

    @patch('galaxy_ng.app.tasks.index_registry.container_models.ContainerDistribution.objects.get')
    @patch('galaxy_ng.app.tasks.index_registry.container_models.ContainerRepository.get_pulp_type')
    def test_existing_local_container(self, mock_get_pulp_type, mock_distro_get):
        mock_get_pulp_type.return_value = 'container.container'
        self.repo.pulp_type = 'local.container'  # Local type
        self.distro.repository = self.repo
        mock_distro_get.return_value = self.distro

        with pytest.raises(CouldNotCreateContainerError) as exc_info:
            create_or_update_remote_container(
                self.container_data, self.registry_pk, self.request_data
            )

        self.assertIn("local container", str(exc_info.value.message))

    @patch('galaxy_ng.app.tasks.index_registry.container_models.ContainerDistribution.objects.get')
    @patch('galaxy_ng.app.tasks.index_registry._get_request')
    @patch('galaxy_ng.app.tasks.index_registry.serializers.ContainerRemoteSerializer')
    @patch('galaxy_ng.app.tasks.index_registry._update_distro_readme_and_description')
    def test_create_new_container(self, mock_update_distro, mock_serializer_class,
                                  mock_get_request, mock_distro_get):
        # First call raises ObjectDoesNotExist, second call returns distro
        mock_distro_get.side_effect = [ObjectDoesNotExist(), self.distro]

        mock_request = Mock()
        mock_get_request.return_value = mock_request

        mock_serializer = Mock()
        mock_serializer_class.return_value = mock_serializer
        mock_serializer.is_valid.return_value = True
        mock_serializer.validated_data = {'test': 'data'}

        create_or_update_remote_container(self.container_data, self.registry_pk, self.request_data)

        mock_get_request.assert_called_once_with(self.request_data)
        mock_serializer_class.assert_called_once_with(
            data={
                "name": "test-container",
                "upstream_name": "test-container",
                "registry": "123"
            },
            context={"request": mock_request}
        )
        mock_serializer.is_valid.assert_called_once_with(raise_exception=True)
        mock_serializer.create.assert_called_once_with({'test': 'data'})
        mock_update_distro.assert_called_once_with(self.distro, self.container_data)


class TestIndexExecutionEnvironments(TestCase):

    def setUp(self):
        self.registry_pk = 123
        self.request_data = {'user': Mock(), 'method': 'POST'}
        self.registry = Mock()

        # Sample API response data
        self.page1_data = {
            'data': [
                {
                    'repository': 'test-ee-1',
                    'display_data': {
                        'short_description': 'Test EE 1',
                        'long_description_markdown': '# Test EE 1'
                    }
                }
            ],
            'page_size': 1
        }

        self.page2_data = {
            'data': [],
            'page_size': 1
        }

    @patch('galaxy_ng.app.tasks.index_registry.models.ContainerRegistryRemote.objects.get')
    @patch('galaxy_ng.app.tasks.index_registry.dispatch')
    @patch('galaxy_ng.app.tasks.index_registry.json.load')
    @patch('builtins.open', new_callable=mock_open)
    def test_index_execution_environments_single_page(self, mock_file_open, mock_json_load,
                                                      mock_dispatch, mock_registry_get):
        mock_registry_get.return_value = self.registry

        # Mock downloader
        mock_downloader = Mock()
        mock_download_result = Mock()
        mock_download_result.path = '/tmp/test.json'
        mock_downloader.fetch.return_value = mock_download_result
        self.registry.get_downloader.return_value = mock_downloader

        # Mock JSON response - only one page with no more data
        empty_page_data = {'data': [], 'page_size': 50}
        mock_json_load.return_value = empty_page_data

        index_execution_environments_from_redhat_registry(self.registry_pk, self.request_data)

        mock_registry_get.assert_called_once_with(pk=self.registry_pk)

        # Should call get_downloader with proper URL
        expected_query = {
            "filter": (
                "build_categories=in=('Automation execution environment') "
                "and release_categories=in=('Generally Available')"
            ),
            "page": 0,
            "sort_by": "creation_date[asc]"
        }
        expected_url = CATALOG_API + "?" + urlencode(expected_query, quote_via=quote)
        self.registry.get_downloader.assert_called_once_with(url=expected_url)

        mock_dispatch.assert_not_called()  # No containers to dispatch

    @patch('galaxy_ng.app.tasks.index_registry.models.ContainerRegistryRemote.objects.get')
    @patch('galaxy_ng.app.tasks.index_registry.dispatch')
    @patch('galaxy_ng.app.tasks.index_registry.json.load')
    @patch('builtins.open', new_callable=mock_open)
    def test_index_execution_environments_multiple_pages(self, mock_file_open, mock_json_load,
                                                         mock_dispatch, mock_registry_get):
        mock_registry_get.return_value = self.registry

        # Mock downloader
        mock_downloader = Mock()
        mock_download_result = Mock()
        mock_download_result.path = '/tmp/test.json'
        mock_downloader.fetch.return_value = mock_download_result
        self.registry.get_downloader.return_value = mock_downloader

        # Mock JSON responses - first page has data, second page is empty
        mock_json_load.side_effect = [self.page1_data, self.page2_data]

        index_execution_environments_from_redhat_registry(self.registry_pk, self.request_data)

        # Should call get_downloader twice (page 0 and page 1)
        self.assertEqual(self.registry.get_downloader.call_count, 2)

        # Should dispatch one task for the container found
        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args

        self.assertEqual(call_args[0][0].__name__, 'create_or_update_remote_container')
        self.assertEqual(call_args[1]['kwargs']['container_data']['name'], 'test-ee-1')
        self.assertEqual(call_args[1]['kwargs']['registry_pk'], self.registry.pk)
        self.assertEqual(call_args[1]['kwargs']['request_data'], self.request_data)
        self.assertEqual(call_args[1]['exclusive_resources'], ["/api/v3/distributions/"])

    @patch('galaxy_ng.app.tasks.index_registry.models.ContainerRegistryRemote.objects.get')
    @patch('galaxy_ng.app.tasks.index_registry.dispatch')
    @patch('galaxy_ng.app.tasks.index_registry.json.load')
    @patch('builtins.open', new_callable=mock_open)
    def test_index_execution_environments_full_page(self, mock_file_open, mock_json_load,
                                                    mock_dispatch, mock_registry_get):
        mock_registry_get.return_value = self.registry

        # Mock downloader
        mock_downloader = Mock()
        mock_download_result = Mock()
        mock_download_result.path = '/tmp/test.json'
        mock_downloader.fetch.return_value = mock_download_result
        self.registry.get_downloader.return_value = mock_downloader

        # Full page (same length as page_size) should trigger next page
        full_page_data = {
            'data': [self.page1_data['data'][0]],  # One item
            'page_size': 1  # Page size is 1, so it's full
        }
        empty_page_data = {'data': [], 'page_size': 1}
        mock_json_load.side_effect = [full_page_data, empty_page_data]

        index_execution_environments_from_redhat_registry(self.registry_pk, self.request_data)

        # Should call twice - once for page 0, once for page 1
        self.assertEqual(self.registry.get_downloader.call_count, 2)
        mock_dispatch.assert_called_once()

    @patch('galaxy_ng.app.tasks.index_registry.models.ContainerRegistryRemote.objects.get')
    def test_index_execution_environments_registry_not_found(self, mock_registry_get):
        mock_registry_get.side_effect = ObjectDoesNotExist()

        with pytest.raises(ObjectDoesNotExist):
            index_execution_environments_from_redhat_registry(self.registry_pk, self.request_data)
