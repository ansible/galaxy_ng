from django.db.models import Count, F, Func
from rest_framework import mixins, serializers
from django_filters import filters
from django_filters.rest_framework import DjangoFilterBackend, filterset

from pulp_ansible.app.models import CollectionVersion

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui.v1 import versioning
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.v1.models import LegacyRoleTag
from galaxy_ng.app.api.v1.serializers import LegacyRoleTagSerializer


class Unnest(Func):
    """PostgreSQL unnest() function to expand array elements into rows."""
    function = 'unnest'
    arity = 1


class CollectionTagSerializer(serializers.Serializer):
    """Serializer for tags extracted from CollectionVersion.tags ArrayField."""
    name = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True, default=0)


class TagsViewSet(api_base.GenericViewSet):
    """Returns distinct tag names from all CollectionVersions."""
    serializer_class = CollectionTagSerializer
    permission_classes = [access_policy.TagsAccessPolicy]
    versioning_class = versioning.UIVersioning

    def get_queryset(self):
        return (
            CollectionVersion.objects
            .exclude(tags=[])
            .exclude(tags__isnull=True)
            .annotate(tag_name=Unnest('tags'))
            .values('tag_name')
            .annotate(name=F('tag_name'), count=Count('pk'))
            .values('name', 'count')
            .order_by('name')
        )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)


class CollectionTagFilterOrdering(filters.OrderingFilter):
    def filter(self, qs, value):
        if value is not None and any(v in ["count", "-count"] for v in value):
            order = "-" if "-count" in value else ""
            return qs.order_by(f"{order}count")

        return super().filter(qs, value)


class CollectionTagFilter(filterset.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='exact')
    name__icontains = filters.CharFilter(field_name='name', lookup_expr='icontains')
    name__contains = filters.CharFilter(field_name='name', lookup_expr='contains')
    name__startswith = filters.CharFilter(field_name='name', lookup_expr='startswith')

    sort = CollectionTagFilterOrdering(
        fields=(
            ("name", "name"),
            ('count', 'count')
        ),
    )

    class Meta:
        # No model - works on annotated queryset
        fields = []


class CollectionsTagsViewSet(
    api_base.GenericViewSet,
    mixins.ListModelMixin
):
    """
    ViewSet for collections' tags within the system.

    Uses a two-phase approach:
    1. Unnest tags and aggregate to get distinct tag names with counts
    2. Filter the aggregated results using Python (since PostgreSQL doesn't
       allow filtering on set-returning functions in WHERE clauses, and
       HAVING requires the filter to be on aggregate functions)

    The filtering happens after aggregation but before pagination to ensure
    correct results while working within PostgreSQL's limitations.
    """
    serializer_class = CollectionTagSerializer
    permission_classes = [access_policy.TagsAccessPolicy]
    versioning_class = versioning.UIVersioning
    filter_backends = (DjangoFilterBackend,)
    filterset_class = CollectionTagFilter

    def get_queryset(self):
        """
        Build the base queryset with unnest and aggregation.
        Filtering is applied separately on the aggregated results.
        """
        qs = (
            CollectionVersion.objects
            .filter(
                ansible_crossrepositorycollectionversionindex__is_highest=True
            )
            .exclude(tags=[])
            .exclude(tags__isnull=True)
            .annotate(tag_name=Unnest('tags'))
            .values('tag_name')
            .annotate(
                name=F('tag_name'),
                count=Count('pk', distinct=True)
            )
            .values('name', 'count')
            .order_by('name')
        )
        return qs

    def list(self, request, *args, **kwargs):
        """List tags with filtering and sorting support."""
        qs = self.get_queryset()

        # Get filter parameters
        name_exact = request.query_params.get('name')
        name_icontains = request.query_params.get('name__icontains')
        name_contains = request.query_params.get('name__contains')
        name_startswith = request.query_params.get('name__startswith')

        # Convert queryset to list for Python-based filtering
        # This is necessary because PostgreSQL doesn't allow WHERE on
        # set-returning functions, and we need to filter the unnested results
        all_tags = list(qs)

        # Apply name filters on the aggregated results
        if name_exact:
            all_tags = [t for t in all_tags if t['name'] == name_exact]
        elif name_icontains:
            name_lower = name_icontains.lower()
            all_tags = [t for t in all_tags if name_lower in t['name'].lower()]
        elif name_contains:
            all_tags = [t for t in all_tags if name_contains in t['name']]
        elif name_startswith:
            all_tags = [t for t in all_tags if t['name'].startswith(name_startswith)]

        # Apply sorting
        sort_param = request.query_params.get('sort', 'name')
        reverse = sort_param.startswith('-')
        sort_field = sort_param.lstrip('-')

        if sort_field in ('name', 'count'):
            all_tags = sorted(all_tags, key=lambda x: x[sort_field], reverse=reverse)

        # Manual pagination since we're working with a list
        page = self.paginate_queryset(all_tags)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(all_tags, many=True)
        return self.get_response(serializer.data)


class RoleTagFilterOrdering(filters.OrderingFilter):
    def filter(self, qs, value):
        if value is not None and any(v in ["count", "-count"] for v in value):
            order = "-" if "-count" in value else ""

            return qs.annotate(count=Count('legacyrole')).order_by(f"{order}count")

        return super().filter(qs, value)


class RoleTagFilter(filterset.FilterSet):
    sort = RoleTagFilterOrdering(
        fields=(
            ("name", "name"),
            ('count', 'count')
        ),
    )

    class Meta:
        model = LegacyRoleTag
        fields = {
            "name": ["exact", "icontains", "contains", "startswith"],
        }


class RolesTagsViewSet(
    api_base.GenericViewSet,
    mixins.ListModelMixin
):
    """
    ViewSet for roles' tags within the system.
    Tags can be populated manually by running `django-admin populate-role-tags`.
    """
    queryset = LegacyRoleTag.objects.all()
    serializer_class = LegacyRoleTagSerializer
    permission_classes = [access_policy.TagsAccessPolicy]
    versioning_class = versioning.UIVersioning
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RoleTagFilter

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.annotate(count=Count("legacyrole"))
