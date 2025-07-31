from unittest.mock import Mock, patch
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request

from galaxy_ng.app.api.ui.v1.views.search import (
    SearchListView,
    FILTER_PARAMS,
    SORTABLE_FIELDS,
    DEFAULT_SEARCH_TYPE,
    RANK_NORMALIZATION,
)


class TestSearchListView(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = SearchListView()

    def test_get_filter_params_basic(self):
        django_request = self.factory.get('/', {
            'keywords': 'test',
            'type': 'collection',
            'deprecated': 'true'
        })
        request = Request(django_request)
        self.view.request = request

        result = self.view.get_filter_params(request)

        expected = {
            'keywords': 'test',
            'type': 'collection',
            'deprecated': 'true'
        }
        assert result == expected

    def test_get_filter_params_with_tags(self):
        django_request = self.factory.get('/', {
            'keywords': 'test',
            'tags': ['tag1', 'tag2', 'tag3']
        })
        request = Request(django_request)
        self.view.request = request

        result = self.view.get_filter_params(request)

        expected = {
            'keywords': 'test',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        assert result == expected

    def test_get_filter_params_ignores_invalid_params(self):
        django_request = self.factory.get('/', {
            'keywords': 'test',
            'invalid_param': 'should_be_ignored',
            'another_invalid': 'also_ignored'
        })
        request = Request(django_request)
        self.view.request = request

        result = self.view.get_filter_params(request)

        expected = {'keywords': 'test'}
        assert result == expected

    def test_get_filter_params_case_insensitive(self):
        django_request = self.factory.get('/', {
            'KEYWORDS': 'test',
            'Type': 'collection'
        })
        request = Request(django_request)
        self.view.request = request

        result = self.view.get_filter_params(request)

        expected = {
            'keywords': 'test',
            'type': 'collection'
        }
        assert result == expected

    def test_get_sorting_param_default_websearch(self):
        django_request = self.factory.get('/')
        request = Request(django_request)
        self.view.request = request

        result = self.view.get_sorting_param(request)

        assert result == ['-download_count', '-relevance']

    def test_get_sorting_param_default_sql(self):
        django_request = self.factory.get('/', {'search_type': 'sql'})
        request = Request(django_request)
        self.view.request = request

        result = self.view.get_sorting_param(request)

        assert result == ['-download_count', '-last_updated']

    def test_get_sorting_param_custom_valid(self):
        django_request = self.factory.get('/', {'order_by': 'name,-namespace_name'})
        request = Request(django_request)
        self.view.request = request

        result = self.view.get_sorting_param(request)

        assert result == ['name', '-namespace_name']

    def test_get_sorting_param_invalid_field(self):
        django_request = self.factory.get('/', {'order_by': 'invalid_field'})
        request = Request(django_request)
        self.view.request = request

        with self.assertRaises(ValidationError) as cm:  # noqa: PT027
            self.view.get_sorting_param(request)

        assert 'order_by requires one of' in str(cm.exception)

    def test_get_sorting_param_relevance_with_sql_search(self):
        django_request = self.factory.get('/', {
            'search_type': 'sql',
            'order_by': 'relevance'
        })
        request = Request(django_request)
        self.view.request = request

        with self.assertRaises(ValidationError) as cm:  # noqa: PT027
            self.view.get_sorting_param(request)

        assert 'relevance\' works only with \'search_type=websearch' in str(cm.exception)

    def test_get_sorting_param_relevance_with_websearch(self):
        django_request = self.factory.get('/', {
            'search_type': 'websearch',
            'order_by': 'relevance'
        })
        request = Request(django_request)
        self.view.request = request

        result = self.view.get_sorting_param(request)

        assert result == ['relevance']

    def test_get_search_results_invalid_type(self):
        request = self.factory.get('/')
        self.view.request = request

        with self.assertRaises(ValidationError) as cm:  # noqa: PT027
            self.view.get_search_results({'type': 'invalid'}, ['-download_count'])

        assert '\'type\' must be [\'collection\', \'role\']' in str(cm.exception)

    def test_get_search_results_invalid_search_type(self):
        request = self.factory.get('/')
        self.view.request = request

        with self.assertRaises(ValidationError) as cm:  # noqa: PT027
            self.view.get_search_results({'search_type': 'invalid'}, ['-download_count'])

        assert '\'search_type\' must be [\'sql\', \'websearch\']' in str(cm.exception)

    @patch('galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_collection_queryset')
    @patch('galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_role_queryset')
    @patch('galaxy_ng.app.api.ui.v1.views.search.SearchListView.filter_and_sort')
    def test_get_search_results_valid_collection(
        self, mock_filter_and_sort, mock_get_roles, mock_get_collections
    ):
        request = self.factory.get('/')
        self.view.request = request

        mock_collections = Mock()
        mock_roles = Mock()
        mock_get_collections.return_value = mock_collections
        mock_get_roles.return_value = mock_roles
        mock_filter_and_sort.return_value = Mock()

        filter_params = {'type': 'collection', 'search_type': 'websearch'}
        sort_params = ['-download_count']

        self.view.get_search_results(filter_params, sort_params)

        mock_get_collections.assert_called_once()
        mock_get_roles.assert_called_once()
        mock_filter_and_sort.assert_called_once_with(
            mock_collections, mock_roles, filter_params, sort_params, 'collection', query=None
        )

    @patch('galaxy_ng.app.api.ui.v1.views.search.SearchQuery')
    @patch('galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_collection_queryset')
    @patch('galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_role_queryset')
    @patch('galaxy_ng.app.api.ui.v1.views.search.SearchListView.filter_and_sort')
    def test_get_search_results_with_websearch_keywords(
        self, mock_filter_and_sort, mock_get_roles, mock_get_collections, mock_search_query
    ):
        request = self.factory.get('/')
        self.view.request = request

        mock_query = Mock()
        mock_search_query.return_value = mock_query
        mock_collections = Mock()
        mock_roles = Mock()
        mock_get_collections.return_value = mock_collections
        mock_get_roles.return_value = mock_roles
        mock_filter_and_sort.return_value = Mock()

        filter_params = {
            'type': 'collection',
            'search_type': 'websearch',
            'keywords': 'test keywords'
        }
        sort_params = ['-download_count']

        self.view.get_search_results(filter_params, sort_params)

        mock_search_query.assert_called_once_with('test keywords', search_type='websearch')
        mock_filter_and_sort.assert_called_once_with(
            mock_collections, mock_roles, filter_params, sort_params, 'collection', query=mock_query
        )

    @patch('galaxy_ng.app.api.ui.v1.views.search.CollectionVersion')
    @patch('galaxy_ng.app.api.ui.v1.views.search.AnsibleCollectionDeprecated')
    @patch('galaxy_ng.app.api.ui.v1.views.search.CollectionDownloadCount')
    @patch('galaxy_ng.app.api.ui.v1.views.search.Namespace')
    def test_get_collection_queryset_without_query(
        self, mock_namespace, mock_download_count, mock_deprecated,
        mock_collection_version
    ):
        mock_qs = Mock()
        mock_collection_version.objects.annotate.return_value.values.\
            return_value.filter.return_value = mock_qs

        result = self.view.get_collection_queryset()

        assert result == mock_qs
        mock_collection_version.objects.annotate.assert_called_once()

    @patch('galaxy_ng.app.api.ui.v1.views.search.Func')
    @patch('galaxy_ng.app.api.ui.v1.views.search.CollectionVersion')
    @patch('galaxy_ng.app.api.ui.v1.views.search.AnsibleCollectionDeprecated')
    @patch('galaxy_ng.app.api.ui.v1.views.search.CollectionDownloadCount')
    @patch('galaxy_ng.app.api.ui.v1.views.search.Namespace')
    def test_get_collection_queryset_with_query(
        self, mock_namespace, mock_download_count, mock_deprecated,
        mock_collection_version, mock_func
    ):
        mock_query = Mock()
        mock_qs = Mock()
        mock_collection_version.objects.annotate.return_value.values.\
            return_value.filter.return_value = mock_qs

        result = self.view.get_collection_queryset(query=mock_query)

        assert result == mock_qs
        mock_func.assert_called_once()

    @patch('galaxy_ng.app.api.ui.v1.views.search.LegacyRole')
    def test_get_role_queryset_without_query(self, mock_legacy_role):
        mock_qs = Mock()
        mock_legacy_role.objects.annotate.return_value.values.return_value = mock_qs

        result = self.view.get_role_queryset()

        assert result == mock_qs
        mock_legacy_role.objects.annotate.assert_called_once()

    @patch('galaxy_ng.app.api.ui.v1.views.search.Func')
    @patch('galaxy_ng.app.api.ui.v1.views.search.LegacyRole')
    def test_get_role_queryset_with_query(self, mock_legacy_role, mock_func):
        mock_query = Mock()
        mock_qs = Mock()
        mock_legacy_role.objects.annotate.return_value.values.return_value = mock_qs

        result = self.view.get_role_queryset(query=mock_query)

        assert result == mock_qs
        mock_func.assert_called_once()

    def test_filter_and_sort_invalid_deprecated_filter(self):
        mock_collections = Mock()
        mock_roles = Mock()

        with self.assertRaises(ValidationError) as cm:  # noqa: PT027
            self.view.filter_and_sort(
                mock_collections, mock_roles,
                {'deprecated': 'invalid'}, ['-download_count']
            )

        assert '\'deprecated\' filter must be \'true\' or \'false\'' in str(cm.exception)

    def test_filter_and_sort_deprecated_true(self):
        mock_collections = Mock()
        mock_roles = Mock()
        mock_collections.filter.return_value = mock_collections
        mock_roles.filter.return_value = mock_roles
        mock_collections.union.return_value.order_by.return_value = Mock()

        self.view.filter_and_sort(
            mock_collections, mock_roles,
            {'deprecated': 'true'}, ['-download_count']
        )

        mock_collections.filter.assert_called_with(deprecated=True)
        mock_roles.filter.assert_called_with(deprecated=True)

    def test_filter_and_sort_deprecated_false(self):
        mock_collections = Mock()
        mock_roles = Mock()
        mock_collections.filter.return_value = mock_collections
        mock_roles.filter.return_value = mock_roles
        mock_collections.union.return_value.order_by.return_value = Mock()

        self.view.filter_and_sort(
            mock_collections, mock_roles,
            {'deprecated': 'false'}, ['-download_count']
        )

        mock_collections.filter.assert_called_with(deprecated=False)
        mock_roles.filter.assert_called_with(deprecated=False)

    def test_filter_and_sort_name_filter(self):
        mock_collections = Mock()
        mock_roles = Mock()
        mock_collections.filter.return_value = mock_collections
        mock_roles.filter.return_value = mock_roles
        mock_collections.union.return_value.order_by.return_value = Mock()

        self.view.filter_and_sort(
            mock_collections, mock_roles,
            {'name': 'TestName'}, ['-download_count']
        )

        mock_collections.filter.assert_called_with(name__iexact='TestName')
        mock_roles.filter.assert_called_with(name__iexact='TestName')

    def test_filter_and_sort_namespace_filter(self):
        mock_collections = Mock()
        mock_roles = Mock()
        mock_collections.filter.return_value = mock_collections
        mock_roles.filter.return_value = mock_roles
        mock_collections.union.return_value.order_by.return_value = Mock()

        self.view.filter_and_sort(
            mock_collections, mock_roles,
            {'namespace': 'TestNamespace'}, ['-download_count']
        )

        mock_collections.filter.assert_called_with(namespace_name__iexact='TestNamespace')
        mock_roles.filter.assert_called_with(namespace_name__iexact='TestNamespace')

    def test_filter_and_sort_tags_filter(self):
        mock_collections = Mock()
        mock_roles = Mock()
        mock_collections.filter.return_value = mock_collections
        mock_roles.filter.return_value = mock_roles
        mock_collections.union.return_value.order_by.return_value = Mock()

        self.view.filter_and_sort(
            mock_collections, mock_roles,
            {'tags': ['tag1', 'tag2']}, ['-download_count']
        )

        # Should be called once for tag filtering
        assert mock_collections.filter.call_count == 1
        assert mock_roles.filter.call_count == 1

    def test_filter_and_sort_platform_filter(self):
        mock_collections = Mock()
        mock_roles = Mock()
        mock_collections.filter.return_value = mock_collections
        mock_roles.filter.return_value = mock_roles
        mock_collections.union.return_value.order_by.return_value = Mock()

        self.view.filter_and_sort(
            mock_collections, mock_roles,
            {'platform': 'ubuntu'}, ['-download_count']
        )

        mock_roles.filter.assert_called_with(full_metadata__platforms__icontains='ubuntu')
        mock_collections.filter.assert_called_with(platform_names='ubuntu')

    def test_filter_and_sort_with_query(self):
        mock_query = Mock()
        mock_collections = Mock()
        mock_roles = Mock()
        mock_collections.filter.return_value = mock_collections
        mock_roles.filter.return_value = mock_roles
        mock_collections.union.return_value.order_by.return_value = Mock()

        self.view.filter_and_sort(
            mock_collections, mock_roles,
            {}, ['-download_count'], query=mock_query
        )

        mock_collections.filter.assert_called_with(search=mock_query)
        mock_roles.filter.assert_called_with(search=mock_query)

    def test_filter_and_sort_with_keywords_sql_search(self):
        mock_collections = Mock()
        mock_roles = Mock()
        mock_collections.filter.return_value = mock_collections
        mock_roles.filter.return_value = mock_roles
        mock_collections.union.return_value.order_by.return_value = Mock()

        self.view.filter_and_sort(
            mock_collections, mock_roles,
            {'keywords': 'test keywords'}, ['-download_count']
        )

        # Should be called once for keywords filtering
        mock_collections.filter.assert_called_once()
        mock_roles.filter.assert_called_once()

    def test_filter_and_sort_type_role_only(self):
        mock_collections = Mock()
        mock_roles = Mock()
        mock_roles.order_by.return_value = Mock()

        self.view.filter_and_sort(
            mock_collections, mock_roles,
            {}, ['-download_count'], type_='role'
        )

        mock_roles.order_by.assert_called_with('-download_count')
        mock_collections.union.assert_not_called()

    def test_filter_and_sort_type_collection_only(self):
        mock_collections = Mock()
        mock_roles = Mock()
        mock_collections.order_by.return_value = Mock()

        self.view.filter_and_sort(
            mock_collections, mock_roles,
            {}, ['-download_count'], type_='collection'
        )

        mock_collections.order_by.assert_called_with('-download_count')
        mock_collections.union.assert_not_called()

    def test_filter_and_sort_union_both_types(self):
        mock_collections = Mock()
        mock_roles = Mock()
        mock_union_qs = Mock()
        mock_final_qs = Mock()
        mock_collections.union.return_value = mock_union_qs
        mock_union_qs.order_by.return_value = mock_final_qs

        self.view.filter_and_sort(
            mock_collections, mock_roles,
            {}, ['-download_count'], type_=''
        )

        mock_collections.union.assert_called_with(mock_roles, all=True)
        mock_union_qs.order_by.assert_called_with('-download_count')
        result = self.view.filter_and_sort(
            mock_collections, mock_roles,
            {}, ['-download_count'], type_=''
        )
        assert result == mock_final_qs

    @patch('galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_filter_params')
    @patch('galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_sorting_param')
    @patch('galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_search_results')
    def test_get_queryset(self, mock_get_search_results, mock_get_sorting, mock_get_filter):
        request = self.factory.get('/')
        self.view.request = request

        mock_filter_params = {'type': 'collection'}
        mock_sort_params = ['-download_count']
        mock_queryset = Mock()

        mock_get_filter.return_value = mock_filter_params
        mock_get_sorting.return_value = mock_sort_params
        mock_get_search_results.return_value = mock_queryset

        result = self.view.get_queryset()

        mock_get_filter.assert_called_once_with(request)
        mock_get_sorting.assert_called_once_with(request)
        mock_get_search_results.assert_called_once_with(mock_filter_params, mock_sort_params)
        assert result == mock_queryset
        assert self.view.filter_params == mock_filter_params
        assert self.view.sort == mock_sort_params


class TestSearchConstants(TestCase):

    def test_filter_params_list(self):
        expected_params = [
            "keywords", "type", "deprecated", "name", "namespace",
            "tags", "platform", "search_type"
        ]
        assert expected_params == FILTER_PARAMS

    def test_sortable_fields_list(self):
        base_fields = ["name", "namespace_name", "download_count", "last_updated", "relevance"]
        reverse_fields = [f"-{item}" for item in base_fields]
        expected_fields = base_fields + reverse_fields
        assert expected_fields == SORTABLE_FIELDS

    def test_default_search_type(self):
        assert DEFAULT_SEARCH_TYPE == "websearch"

    def test_rank_normalization(self):
        assert RANK_NORMALIZATION == 32


class TestSearchModuleFunctions(TestCase):

    @patch('galaxy_ng.app.api.ui.v1.views.search.SearchListView')
    @patch('builtins.print')
    def test_test_function(self, mock_print, mock_search_view):
        # Import and test the test() function
        from galaxy_ng.app.api.ui.v1.views.search import test

        mock_view_instance = Mock()
        mock_search_view.return_value = mock_view_instance

        mock_queryset = Mock()
        mock_queryset._query = "SELECT * FROM test"
        mock_queryset.count.return_value = 5
        mock_queryset.__getitem__ = Mock(return_value=[{'name': 'test1'}, {'name': 'test2'}])

        mock_view_instance.get_search_results.return_value = mock_queryset

        # Execute the test function
        test()

        # Verify it was called correctly
        mock_view_instance.get_search_results.assert_called_once_with(
            {"type": "", "keywords": "java web"}, sort="-relevance"
        )
        mock_queryset.count.assert_called_once()

        # Verify print statements were called
        assert mock_print.call_count > 0
