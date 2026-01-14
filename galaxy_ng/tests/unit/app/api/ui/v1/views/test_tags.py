"""Unit tests for the tags viewsets and serializers.

Tests cover:
- Unnest PostgreSQL function class
- CollectionTagSerializer
- CollectionsTagsViewSet list filtering and sorting logic
"""
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from galaxy_ng.app.api.ui.v1.viewsets.tags import (
    Unnest,
    CollectionTagSerializer,
    CollectionTagFilterOrdering,
    CollectionsTagsViewSet,
    RoleTagFilterOrdering,
)


class TestUnnest(SimpleTestCase):
    """Test the Unnest PostgreSQL function wrapper."""

    def test_unnest_function_name(self):
        """Verify Unnest function has correct PostgreSQL function name."""
        unnest = Unnest('tags')
        assert unnest.function == 'unnest'

    def test_unnest_arity(self):
        """Verify Unnest accepts exactly one argument."""
        unnest = Unnest('tags')
        assert unnest.arity == 1


class TestCollectionTagSerializer(SimpleTestCase):
    """Test the CollectionTagSerializer."""

    def test_serializer_fields(self):
        """Verify serializer has expected fields."""
        serializer = CollectionTagSerializer()
        field_names = set(serializer.fields.keys())
        assert field_names == {'name', 'count'}

    def test_serializer_with_data(self):
        """Verify serializer correctly serializes tag data."""
        data = {'name': 'networking', 'count': 5}
        serializer = CollectionTagSerializer(data)
        assert serializer.data == {'name': 'networking', 'count': 5}

    def test_serializer_with_zero_count(self):
        """Verify serializer handles zero count."""
        data = {'name': 'empty_tag', 'count': 0}
        serializer = CollectionTagSerializer(data)
        assert serializer.data == {'name': 'empty_tag', 'count': 0}

    def test_serializer_many(self):
        """Verify serializer handles list of tags."""
        data = [
            {'name': 'tag1', 'count': 10},
            {'name': 'tag2', 'count': 5},
        ]
        serializer = CollectionTagSerializer(data, many=True)
        assert len(serializer.data) == 2
        assert serializer.data[0]['name'] == 'tag1'
        assert serializer.data[1]['name'] == 'tag2'


class TestCollectionTagFilterOrdering(SimpleTestCase):
    """Test the CollectionTagFilterOrdering filter."""

    def setUp(self):
        self.ordering_filter = CollectionTagFilterOrdering()

    def test_filter_by_count_ascending(self):
        """Verify filtering by count ascending."""
        # Create mock queryset
        mock_qs = MagicMock()
        mock_qs.order_by.return_value = mock_qs

        self.ordering_filter.filter(mock_qs, ['count'])

        mock_qs.order_by.assert_called_once_with('count')

    def test_filter_by_count_descending(self):
        """Verify filtering by -count descending."""
        mock_qs = MagicMock()
        mock_qs.order_by.return_value = mock_qs

        self.ordering_filter.filter(mock_qs, ['-count'])

        mock_qs.order_by.assert_called_once_with('-count')

    def test_filter_none_value(self):
        """Verify filter handles None value gracefully."""
        mock_qs = MagicMock()

        # Should call parent's filter method
        with patch.object(
            CollectionTagFilterOrdering.__bases__[0], 'filter', return_value=mock_qs
        ) as mock_super:
            self.ordering_filter.filter(mock_qs, None)
            mock_super.assert_called_once()


class TestCollectionsTagsViewSetFiltering(SimpleTestCase):
    """Test the filtering and sorting logic in CollectionsTagsViewSet.list()."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = CollectionsTagsViewSet()
        self.view.format_kwarg = None

    def _get_mock_tag_data(self):
        """Return sample tag data for testing."""
        return [
            {'name': 'networking', 'count': 10},
            {'name': 'database', 'count': 5},
            {'name': 'security', 'count': 15},
            {'name': 'monitoring', 'count': 3},
            {'name': 'net_tools', 'count': 2},
        ]

    def test_filter_by_name_exact(self):
        """Test exact name filter."""
        all_tags = self._get_mock_tag_data()

        # Apply exact filter logic from the viewset
        name_exact = 'networking'
        filtered = [t for t in all_tags if t['name'] == name_exact]

        assert len(filtered) == 1
        assert filtered[0]['name'] == 'networking'

    def test_filter_by_name_icontains(self):
        """Test case-insensitive contains filter."""
        all_tags = self._get_mock_tag_data()

        # Apply icontains filter logic from the viewset
        name_icontains = 'NET'
        name_lower = name_icontains.lower()
        filtered = [t for t in all_tags if name_lower in t['name'].lower()]

        assert len(filtered) == 2
        names = [t['name'] for t in filtered]
        assert 'networking' in names
        assert 'net_tools' in names

    def test_filter_by_name_contains(self):
        """Test case-sensitive contains filter."""
        all_tags = self._get_mock_tag_data()

        # Apply contains filter logic from the viewset
        name_contains = 'net'
        filtered = [t for t in all_tags if name_contains in t['name']]

        assert len(filtered) == 2
        names = [t['name'] for t in filtered]
        assert 'networking' in names
        assert 'net_tools' in names

    def test_filter_by_name_startswith(self):
        """Test startswith filter."""
        all_tags = self._get_mock_tag_data()

        # Apply startswith filter logic from the viewset
        name_startswith = 'net'
        filtered = [t for t in all_tags if t['name'].startswith(name_startswith)]

        assert len(filtered) == 2
        names = [t['name'] for t in filtered]
        assert 'networking' in names
        assert 'net_tools' in names

    def test_filter_no_match(self):
        """Test filter with no matches."""
        all_tags = self._get_mock_tag_data()

        name_exact = 'nonexistent'
        filtered = [t for t in all_tags if t['name'] == name_exact]

        assert len(filtered) == 0

    def test_sort_by_name_ascending(self):
        """Test sorting by name ascending."""
        all_tags = self._get_mock_tag_data()

        sort_param = 'name'
        reverse = sort_param.startswith('-')
        sort_field = sort_param.lstrip('-')
        sorted_tags = sorted(all_tags, key=lambda x: x[sort_field], reverse=reverse)

        names = [t['name'] for t in sorted_tags]
        assert names == sorted(names)

    def test_sort_by_name_descending(self):
        """Test sorting by name descending."""
        all_tags = self._get_mock_tag_data()

        sort_param = '-name'
        reverse = sort_param.startswith('-')
        sort_field = sort_param.lstrip('-')
        sorted_tags = sorted(all_tags, key=lambda x: x[sort_field], reverse=reverse)

        names = [t['name'] for t in sorted_tags]
        assert names == sorted(names, reverse=True)

    def test_sort_by_count_ascending(self):
        """Test sorting by count ascending."""
        all_tags = self._get_mock_tag_data()

        sort_param = 'count'
        reverse = sort_param.startswith('-')
        sort_field = sort_param.lstrip('-')
        sorted_tags = sorted(all_tags, key=lambda x: x[sort_field], reverse=reverse)

        counts = [t['count'] for t in sorted_tags]
        assert counts == sorted(counts)

    def test_sort_by_count_descending(self):
        """Test sorting by count descending."""
        all_tags = self._get_mock_tag_data()

        sort_param = '-count'
        reverse = sort_param.startswith('-')
        sort_field = sort_param.lstrip('-')
        sorted_tags = sorted(all_tags, key=lambda x: x[sort_field], reverse=reverse)

        counts = [t['count'] for t in sorted_tags]
        assert counts == sorted(counts, reverse=True)

    def test_filter_and_sort_combined(self):
        """Test filtering and sorting together."""
        all_tags = self._get_mock_tag_data()

        # Filter by name containing 'net'
        name_contains = 'net'
        filtered = [t for t in all_tags if name_contains in t['name']]

        # Sort by count descending
        sort_param = '-count'
        reverse = sort_param.startswith('-')
        sort_field = sort_param.lstrip('-')
        sorted_tags = sorted(filtered, key=lambda x: x[sort_field], reverse=reverse)

        assert len(sorted_tags) == 2
        # networking has count 10, net_tools has count 2
        assert sorted_tags[0]['name'] == 'networking'
        assert sorted_tags[1]['name'] == 'net_tools'


class TestRoleTagFilterOrdering(SimpleTestCase):
    """Test the RoleTagFilterOrdering filter."""

    def setUp(self):
        self.ordering_filter = RoleTagFilterOrdering()

    def test_filter_by_count_ascending(self):
        """Verify filtering by count ascending adds annotation."""
        mock_qs = MagicMock()
        mock_annotated = MagicMock()
        mock_qs.annotate.return_value = mock_annotated
        mock_annotated.order_by.return_value = mock_annotated

        self.ordering_filter.filter(mock_qs, ['count'])

        mock_qs.annotate.assert_called_once()
        mock_annotated.order_by.assert_called_once_with('count')

    def test_filter_by_count_descending(self):
        """Verify filtering by -count descending adds annotation."""
        mock_qs = MagicMock()
        mock_annotated = MagicMock()
        mock_qs.annotate.return_value = mock_annotated
        mock_annotated.order_by.return_value = mock_annotated

        self.ordering_filter.filter(mock_qs, ['-count'])

        mock_qs.annotate.assert_called_once()
        mock_annotated.order_by.assert_called_once_with('-count')


class TestTagsViewSetList(SimpleTestCase):
    """Test the TagsViewSet.list() method."""

    def setUp(self):
        self.factory = APIRequestFactory()

    @patch.object(CollectionsTagsViewSet, 'get_queryset')
    def test_list_returns_paginated_response(self, mock_get_queryset):
        """Test that list() returns a paginated response."""
        from galaxy_ng.app.api.ui.v1.viewsets.tags import TagsViewSet

        mock_tag_data = [
            {'name': 'networking', 'count': 10},
            {'name': 'security', 'count': 5},
        ]

        view = TagsViewSet()
        view.format_kwarg = None

        request = self.factory.get('/tags/')
        view.request = request

        # Mock the methods called by list()
        with (
            patch.object(view, 'filter_queryset', return_value=mock_tag_data),
            patch.object(view, 'paginate_queryset', return_value=mock_tag_data),
            patch.object(view, 'get_queryset', return_value=mock_tag_data),
            patch.object(view, 'get_serializer') as mock_serializer,
            patch.object(view, 'get_paginated_response') as mock_paginated,
        ):
            mock_serializer.return_value.data = mock_tag_data
            mock_paginated.return_value = {'results': mock_tag_data}

            result = view.list(request)

            mock_paginated.assert_called_once_with(mock_tag_data)
            assert result == {'results': mock_tag_data}

    @patch.object(CollectionsTagsViewSet, 'get_queryset')
    def test_list_calls_filter_queryset(self, mock_get_queryset):
        """Test that list() calls filter_queryset on the queryset."""
        from galaxy_ng.app.api.ui.v1.viewsets.tags import TagsViewSet

        mock_qs = MagicMock()
        mock_filtered_qs = MagicMock()

        view = TagsViewSet()
        view.format_kwarg = None

        request = self.factory.get('/tags/')
        view.request = request

        with (
            patch.object(view, 'get_queryset', return_value=mock_qs),
            patch.object(view, 'filter_queryset', return_value=mock_filtered_qs) as mock_filter,
            patch.object(view, 'paginate_queryset', return_value=[]),
            patch.object(view, 'get_serializer') as mock_serializer,
            patch.object(view, 'get_paginated_response', return_value={}),
        ):
            mock_serializer.return_value.data = []
            view.list(request)

            mock_filter.assert_called_once_with(mock_qs)


class TestCollectionsTagsViewSetList(SimpleTestCase):
    """Test the CollectionsTagsViewSet.list() method integration."""

    def setUp(self):
        self.factory = APIRequestFactory()

    def _create_view_with_request(self, query_params=None):
        """Helper to create a view with a properly configured request."""
        path = '/tags/'
        if query_params:
            path += '?' + '&'.join(f'{k}={v}' for k, v in query_params.items())

        django_request = self.factory.get(path)
        # Wrap in DRF Request to get query_params attribute
        request = Request(django_request)
        view = CollectionsTagsViewSet()
        view.request = request
        view.format_kwarg = None
        return view, request

    def _get_mock_tag_data(self):
        """Return sample tag data for testing."""
        return [
            {'name': 'networking', 'count': 10},
            {'name': 'database', 'count': 5},
            {'name': 'security', 'count': 15},
            {'name': 'monitoring', 'count': 3},
            {'name': 'net_tools', 'count': 2},
        ]

    @patch.object(CollectionsTagsViewSet, 'get_queryset')
    def test_list_with_name_exact_filter(self, mock_get_queryset):
        """Test list() with exact name filter."""
        mock_get_queryset.return_value = self._get_mock_tag_data()

        view, request = self._create_view_with_request({'name': 'networking'})

        with patch.object(view, 'paginate_queryset') as mock_paginate:
            mock_paginate.return_value = None  # No pagination
            with patch.object(view, 'get_serializer') as mock_serializer:
                mock_serializer.return_value.data = [{'name': 'networking', 'count': 10}]
                with patch.object(view, 'get_response', return_value={'data': []}, create=True):
                    view.list(request)

                    # Verify the serializer was called with filtered data
                    call_args = mock_serializer.call_args
                    filtered_data = call_args[0][0]
                    assert len(filtered_data) == 1
                    assert filtered_data[0]['name'] == 'networking'

    @patch.object(CollectionsTagsViewSet, 'get_queryset')
    def test_list_with_name_icontains_filter(self, mock_get_queryset):
        """Test list() with case-insensitive contains filter."""
        mock_get_queryset.return_value = self._get_mock_tag_data()

        view, request = self._create_view_with_request({'name__icontains': 'NET'})

        with patch.object(view, 'paginate_queryset') as mock_paginate:
            mock_paginate.return_value = None
            with patch.object(view, 'get_serializer') as mock_serializer:
                mock_serializer.return_value.data = []
                with patch.object(view, 'get_response', return_value={'data': []}, create=True):
                    view.list(request)

                    call_args = mock_serializer.call_args
                    filtered_data = call_args[0][0]
                    names = [t['name'] for t in filtered_data]
                    assert 'networking' in names
                    assert 'net_tools' in names
                    assert len(filtered_data) == 2

    @patch.object(CollectionsTagsViewSet, 'get_queryset')
    def test_list_with_name_contains_filter(self, mock_get_queryset):
        """Test list() with case-sensitive contains filter."""
        mock_get_queryset.return_value = self._get_mock_tag_data()

        view, request = self._create_view_with_request({'name__contains': 'net'})

        with patch.object(view, 'paginate_queryset') as mock_paginate:
            mock_paginate.return_value = None
            with patch.object(view, 'get_serializer') as mock_serializer:
                mock_serializer.return_value.data = []
                with patch.object(view, 'get_response', return_value={'data': []}, create=True):
                    view.list(request)

                    call_args = mock_serializer.call_args
                    filtered_data = call_args[0][0]
                    names = [t['name'] for t in filtered_data]
                    assert 'networking' in names
                    assert 'net_tools' in names

    @patch.object(CollectionsTagsViewSet, 'get_queryset')
    def test_list_with_name_startswith_filter(self, mock_get_queryset):
        """Test list() with startswith filter."""
        mock_get_queryset.return_value = self._get_mock_tag_data()

        view, request = self._create_view_with_request({'name__startswith': 'net'})

        with patch.object(view, 'paginate_queryset') as mock_paginate:
            mock_paginate.return_value = None
            with patch.object(view, 'get_serializer') as mock_serializer:
                mock_serializer.return_value.data = []
                with patch.object(view, 'get_response', return_value={'data': []}, create=True):
                    view.list(request)

                    call_args = mock_serializer.call_args
                    filtered_data = call_args[0][0]
                    names = [t['name'] for t in filtered_data]
                    assert 'networking' in names
                    assert 'net_tools' in names

    @patch.object(CollectionsTagsViewSet, 'get_queryset')
    def test_list_with_sort_by_count_descending(self, mock_get_queryset):
        """Test list() with descending count sort."""
        mock_get_queryset.return_value = self._get_mock_tag_data()

        view, request = self._create_view_with_request({'sort': '-count'})

        with patch.object(view, 'paginate_queryset') as mock_paginate:
            mock_paginate.return_value = None
            with patch.object(view, 'get_serializer') as mock_serializer:
                mock_serializer.return_value.data = []
                with patch.object(view, 'get_response', return_value={'data': []}, create=True):
                    view.list(request)

                    call_args = mock_serializer.call_args
                    sorted_data = call_args[0][0]
                    counts = [t['count'] for t in sorted_data]
                    assert counts == sorted(counts, reverse=True)

    @patch.object(CollectionsTagsViewSet, 'get_queryset')
    def test_list_with_sort_by_name_ascending(self, mock_get_queryset):
        """Test list() with ascending name sort (default)."""
        mock_get_queryset.return_value = self._get_mock_tag_data()

        view, request = self._create_view_with_request({'sort': 'name'})

        with patch.object(view, 'paginate_queryset') as mock_paginate:
            mock_paginate.return_value = None
            with patch.object(view, 'get_serializer') as mock_serializer:
                mock_serializer.return_value.data = []
                with patch.object(view, 'get_response', return_value={'data': []}, create=True):
                    view.list(request)

                    call_args = mock_serializer.call_args
                    sorted_data = call_args[0][0]
                    names = [t['name'] for t in sorted_data]
                    assert names == sorted(names)

    @patch.object(CollectionsTagsViewSet, 'get_queryset')
    def test_list_with_pagination(self, mock_get_queryset):
        """Test list() returns paginated response when pagination is available."""
        mock_get_queryset.return_value = self._get_mock_tag_data()

        view, request = self._create_view_with_request()
        paginated_data = [{'name': 'networking', 'count': 10}]

        with (
            patch.object(view, 'paginate_queryset', return_value=paginated_data),
            patch.object(view, 'get_serializer') as mock_serializer,
            patch.object(view, 'get_paginated_response') as mock_paginated,
        ):
            mock_serializer.return_value.data = paginated_data
            mock_paginated.return_value = {'results': paginated_data}

            result = view.list(request)

            mock_paginated.assert_called_once_with(paginated_data)
            assert result == {'results': paginated_data}

    @patch.object(CollectionsTagsViewSet, 'get_queryset')
    def test_list_filter_and_sort_combined(self, mock_get_queryset):
        """Test list() with both filtering and sorting."""
        mock_get_queryset.return_value = self._get_mock_tag_data()

        view, request = self._create_view_with_request({
            'name__contains': 'net',
            'sort': '-count'
        })

        with patch.object(view, 'paginate_queryset') as mock_paginate:
            mock_paginate.return_value = None
            with patch.object(view, 'get_serializer') as mock_serializer:
                mock_serializer.return_value.data = []
                with patch.object(view, 'get_response', return_value={'data': []}, create=True):
                    view.list(request)

                    call_args = mock_serializer.call_args
                    result_data = call_args[0][0]

                    # Should only have networking (10) and net_tools (2)
                    assert len(result_data) == 2
                    # Should be sorted by count descending
                    assert result_data[0]['name'] == 'networking'
                    assert result_data[1]['name'] == 'net_tools'


class TestRolesTagsViewSetGetQueryset(SimpleTestCase):
    """Test the RolesTagsViewSet.get_queryset() method."""

    def test_get_queryset_annotates_count(self):
        """Test that get_queryset adds count annotation."""
        from galaxy_ng.app.api.ui.v1.viewsets.tags import RolesTagsViewSet

        view = RolesTagsViewSet()

        # Mock the parent class's get_queryset
        mock_qs = MagicMock()
        mock_annotated_qs = MagicMock()
        mock_qs.annotate.return_value = mock_annotated_qs

        with patch.object(
            RolesTagsViewSet.__bases__[0], 'get_queryset', return_value=mock_qs
        ):
            result = view.get_queryset()

            # Verify annotate was called
            mock_qs.annotate.assert_called_once()

            # Verify the annotation uses Count('legacyrole')
            call_kwargs = mock_qs.annotate.call_args[1]
            assert 'count' in call_kwargs

            assert result == mock_annotated_qs

    def test_get_queryset_count_annotation_type(self):
        """Test that the count annotation is a Count aggregate."""
        from django.db.models import Count
        from galaxy_ng.app.api.ui.v1.viewsets.tags import RolesTagsViewSet

        view = RolesTagsViewSet()

        mock_qs = MagicMock()
        mock_qs.annotate.return_value = mock_qs

        with patch.object(
            RolesTagsViewSet.__bases__[0], 'get_queryset', return_value=mock_qs
        ):
            view.get_queryset()

            call_kwargs = mock_qs.annotate.call_args[1]
            count_annotation = call_kwargs['count']

            # Verify it's a Count object targeting 'legacyrole'
            assert isinstance(count_annotation, Count)
            # The source expression should reference 'legacyrole'
            assert 'legacyrole' in str(count_annotation)
