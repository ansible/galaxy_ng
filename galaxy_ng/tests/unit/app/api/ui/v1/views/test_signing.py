from unittest.mock import Mock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from galaxy_ng.app.api.ui.v1.views.signing import CollectionSignView


class TestCollectionSignView(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = CollectionSignView()
        self.view.kwargs = {}  # Initialize kwargs
        self.signing_service = Mock()
        self.repository = Mock()
        self.distribution = Mock()
        self.task = Mock()
        self.task.pk = "test-task-id"

        # Setup mock content queryset
        self.content_queryset = Mock()
        self.repository.content = self.content_queryset

    def test_init(self):
        """Test that the view is properly initialized."""
        self.assertEqual(self.view.action, "sign")

    @patch('galaxy_ng.app.api.ui.v1.views.signing.call_sign_task')
    @patch.object(CollectionSignView, '_get_signing_service')
    @patch.object(CollectionSignView, 'get_repository')
    @patch.object(CollectionSignView, '_get_content_units_to_sign')
    def test_post_success(self, mock_get_content_units, mock_get_repository,
                          mock_get_signing_service, mock_call_sign_task):
        """Test successful POST request."""
        mock_get_signing_service.return_value = self.signing_service
        mock_get_repository.return_value = self.repository
        mock_get_content_units.return_value = ["unit1", "unit2"]
        mock_call_sign_task.return_value = self.task

        request_data = {
            "signing_service": "test-service",
            "distro_base_path": "test-distro"
        }
        wsgi_request = self.factory.post('/api/ui/v1/collection_signing/', request_data)
        request = Request(wsgi_request)
        request._full_data = request_data

        response = self.view.post(request)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data, {"task_id": "test-task-id"})

        mock_get_signing_service.assert_called_once_with(request)
        mock_get_repository.assert_called_once_with(request)
        mock_get_content_units.assert_called_once_with(request, self.repository)
        mock_call_sign_task.assert_called_once_with(
            self.signing_service, self.repository, ["unit1", "unit2"]
        )

    @patch('galaxy_ng.app.api.ui.v1.views.signing.SigningService.objects.get')
    def test_get_signing_service_success(self, mock_signing_service_get):
        """Test successful signing service retrieval."""
        mock_signing_service_get.return_value = self.signing_service

        request_data = {"signing_service": "test-service"}
        wsgi_request = self.factory.post('/', request_data)
        request = Request(wsgi_request)
        request._full_data = request_data

        result = self.view._get_signing_service(request)

        self.assertEqual(result, self.signing_service)
        mock_signing_service_get.assert_called_once_with(name="test-service")

    @patch('galaxy_ng.app.api.ui.v1.views.signing.AnsibleDistribution.objects.get')
    def test_get_repository_success(self, mock_distribution_get):
        """Test successful repository retrieval."""
        self.distribution.repository = self.repository
        mock_distribution_get.return_value = self.distribution

        request_data = {"distro_base_path": "test-distro"}
        wsgi_request = self.factory.post('/', request_data)
        request = Request(wsgi_request)
        request._full_data = request_data

        result = self.view.get_repository(request)

        self.assertEqual(result, self.repository)
        mock_distribution_get.assert_called_once_with(base_path="test-distro")

    @patch('galaxy_ng.app.api.ui.v1.views.signing.AnsibleDistribution.objects.get')
    def test_get_repository_from_kwargs(self, mock_distribution_get):
        """Test repository retrieval from URL kwargs."""
        self.distribution.repository = self.repository
        mock_distribution_get.return_value = self.distribution
        self.view.kwargs = {"path": "kwargs-distro"}

        wsgi_request = self.factory.post('/', {})
        request = Request(wsgi_request)
        request._full_data = {}

        result = self.view.get_repository(request)

        self.assertEqual(result, self.repository)
        mock_distribution_get.assert_called_once_with(base_path="kwargs-distro")

    def test_get_content_units_to_sign_from_request_data(self):
        """Test content units retrieval when specified in request data."""
        request_data = {"content_units": ["unit1", "unit2", "unit3"]}
        wsgi_request = self.factory.post('/', request_data)
        request = Request(wsgi_request)
        request._full_data = request_data

        result = self.view._get_content_units_to_sign(request, self.repository)

        self.assertEqual(result, ["unit1", "unit2", "unit3"])

    def test_get_content_units_to_sign_wildcard(self):
        """Test content units retrieval with wildcard."""
        request_data = {"content_units": ["*"]}
        wsgi_request = self.factory.post('/', request_data)
        request = Request(wsgi_request)
        request._full_data = request_data

        result = self.view._get_content_units_to_sign(request, self.repository)

        self.assertEqual(result, ["*"])

    def test_get_content_units_by_namespace_from_request(self):
        """Test content units retrieval by namespace from request data."""
        request_data = {"namespace": "test-namespace"}
        wsgi_request = self.factory.post('/', request_data)
        request = Request(wsgi_request)
        request._full_data = request_data
        self.view.kwargs = {}

        # Mock repository content filter
        mock_queryset = Mock()
        mock_queryset.values_list.return_value = [1, 2, 3]
        self.content_queryset.filter.return_value = mock_queryset

        result = self.view._get_content_units_to_sign(request, self.repository)

        expected_query = {
            "pulp_type": "ansible.collection_version",
            "ansible_collectionversion__namespace": "test-namespace",
        }
        self.content_queryset.filter.assert_called_once_with(**expected_query)
        mock_queryset.values_list.assert_called_once_with("pk", flat=True)
        self.assertEqual(result, ["1", "2", "3"])

    def test_get_content_units_by_namespace_from_kwargs(self):
        """Test content units retrieval by namespace from URL kwargs."""
        wsgi_request = self.factory.post('/', {})
        request = Request(wsgi_request)
        request._full_data = {}
        self.view.kwargs = {"namespace": "kwargs-namespace"}

        # Mock repository content filter
        mock_queryset = Mock()
        mock_queryset.values_list.return_value = [4, 5]
        self.content_queryset.filter.return_value = mock_queryset

        result = self.view._get_content_units_to_sign(request, self.repository)

        expected_query = {
            "pulp_type": "ansible.collection_version",
            "ansible_collectionversion__namespace": "kwargs-namespace",
        }
        self.content_queryset.filter.assert_called_once_with(**expected_query)
        self.assertEqual(result, ["4", "5"])

    def test_get_content_units_with_collection(self):
        """Test content units retrieval with namespace and collection."""
        request_data = {"namespace": "test-namespace", "collection": "test-collection"}
        wsgi_request = self.factory.post('/', request_data)
        request = Request(wsgi_request)
        request._full_data = request_data
        self.view.kwargs = {}

        # Mock repository content filter
        mock_queryset = Mock()
        mock_queryset.values_list.return_value = [6, 7]
        self.content_queryset.filter.return_value = mock_queryset

        result = self.view._get_content_units_to_sign(request, self.repository)

        expected_query = {
            "pulp_type": "ansible.collection_version",
            "ansible_collectionversion__namespace": "test-namespace",
            "ansible_collectionversion__name": "test-collection",
        }
        self.content_queryset.filter.assert_called_once_with(**expected_query)
        self.assertEqual(result, ["6", "7"])

    def test_get_content_units_with_version(self):
        """Test content units retrieval with namespace, collection, and version."""
        request_data = {
            "namespace": "test-namespace",
            "collection": "test-collection",
            "version": "1.0.0"
        }
        wsgi_request = self.factory.post('/', request_data)
        request = Request(wsgi_request)
        request._full_data = request_data
        self.view.kwargs = {}

        # Mock repository content filter
        mock_queryset = Mock()
        mock_queryset.values_list.return_value = [8]
        self.content_queryset.filter.return_value = mock_queryset

        result = self.view._get_content_units_to_sign(request, self.repository)

        expected_query = {
            "pulp_type": "ansible.collection_version",
            "ansible_collectionversion__namespace": "test-namespace",
            "ansible_collectionversion__name": "test-collection",
            "ansible_collectionversion__version": "1.0.0",
        }
        self.content_queryset.filter.assert_called_once_with(**expected_query)
        self.assertEqual(result, ["8"])

    def test_get_content_units_only_namespace_and_collection(self):
        """Test content units retrieval with only namespace and collection (no version)."""
        request_data = {"namespace": "test-namespace", "collection": "test-collection"}
        wsgi_request = self.factory.post('/', request_data)
        request = Request(wsgi_request)
        request._full_data = request_data
        self.view.kwargs = {}

        # Mock repository content filter
        mock_queryset = Mock()
        mock_queryset.values_list.return_value = [11, 12, 13]
        self.content_queryset.filter.return_value = mock_queryset

        result = self.view._get_content_units_to_sign(request, self.repository)

        expected_query = {
            "pulp_type": "ansible.collection_version",
            "ansible_collectionversion__namespace": "test-namespace",
            "ansible_collectionversion__name": "test-collection",
        }
        self.content_queryset.filter.assert_called_once_with(**expected_query)
        self.assertEqual(result, ["11", "12", "13"])

    def test_get_content_units_empty_strings_treated_as_missing(self):
        """Test that empty strings are treated as missing values."""
        request_data = {
            "namespace": "test-namespace",
            "collection": "",  # Empty string
            "version": ""      # Empty string
        }
        wsgi_request = self.factory.post('/', request_data)
        request = Request(wsgi_request)
        request._full_data = request_data
        self.view.kwargs = {}

        # Mock repository content filter
        mock_queryset = Mock()
        mock_queryset.values_list.return_value = [14, 15]
        self.content_queryset.filter.return_value = mock_queryset

        result = self.view._get_content_units_to_sign(request, self.repository)

        # Should only include namespace, not collection or version since they are empty
        expected_query = {
            "pulp_type": "ansible.collection_version",
            "ansible_collectionversion__namespace": "test-namespace",
        }
        self.content_queryset.filter.assert_called_once_with(**expected_query)
        self.assertEqual(result, ["14", "15"])
