from itertools import chain
from gettext import gettext as _

from django.db.models import Count
from rest_framework import serializers
from rest_framework import mixins
from django_filters import filters
from django_filters.rest_framework import DjangoFilterBackend, filterset

from pulp_ansible.app.models import Tag
from pulp_ansible.app.serializers import TagSerializer

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui import versioning
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.v1.models import LegacyRole


class TagsViewSet(api_base.GenericViewSet):
    serializer_class = TagSerializer
    permission_classes = [access_policy.TagsAccessPolicy]
    versioning_class = versioning.UIVersioning

    queryset = Tag.objects.all()

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)


class TagFilterOrdering(filters.OrderingFilter):
    def filter(self, qs, value):
        if value is not None and any(v in ["count", "-count"] for v in value):
            order = "-" if "-count" in value else ""

            return qs.filter(
                ansible_collectionversion__ansible_crossrepositorycollectionversionindex__is_highest=True  # noqa: E501
            ).annotate(count=Count('ansible_collectionversion')).order_by(f"{order}count")

        return super().filter(qs, value)


class TagFilter(filterset.FilterSet):
    sort = TagFilterOrdering(
        fields=(
            ("name", "name"),
            ('count', 'count')
        ),
    )

    class Meta:
        model = Tag
        fields = {
            "name": ["exact", "icontains", "contains", "startswith"],
        }


class CollectionsTagsViewSet(
    api_base.GenericViewSet,
    mixins.ListModelMixin
):
    """
    ViewSet for collections' tags within the system.
    """
    serializer_class = TagSerializer
    permission_classes = [access_policy.TagsAccessPolicy]
    versioning_class = versioning.UIVersioning
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TagFilter

    queryset = Tag.objects.all()


class RolesTagsViewSet(api_base.GenericViewSet):
    """
    ViewSet for roles' tags within the system.
    """
    queryset = LegacyRole.objects.all()
    permission_classes = [access_policy.TagsAccessPolicy]
    versioning_class = versioning.UIVersioning
    filter_backends = (DjangoFilterBackend,)

    ordering_fields = ["name", "count"]
    ordering = ["name"]
    filter_fields = ["exact", "icontains", "contains", "startswith"]

    def _filter_queryset(self, queryset, request):
        """
            Custom sorting and filtering,
            must be performed manually since
            we are overwriting the queryset with a list of tags.
        """

        query_params = request.query_params.copy()
        sort = query_params.get("sort")
        if sort:
            query_params.pop("sort")

        # filtering
        if value := query_params.get("name"):
            queryset = list(filter(lambda x: x["name"] == value, queryset))
        elif value := query_params.get("name__contains"):
            queryset = list(filter(lambda x: value in x["name"], queryset))
        elif value := query_params.get("name__icontains"):
            queryset = list(filter(lambda x: value.lower() in x["name"].lower(), queryset))
        elif value := query_params.get("name__startswith"):
            queryset = list(filter(lambda x: x["name"].startswith(value), queryset))

        # sorting
        if sort is not None and sort in ["name", "-name", "count", "-count"]:
            reverse = True if "-" in sort else False
            sort_field = sort.replace("-", "")
            queryset = sorted(queryset, key=lambda x: x[sort_field], reverse=reverse)
        elif sort is not None:
            raise serializers.ValidationError(_(f"Invalid Sort: '{sort}'"))

        return queryset

    def list(self, request, *args, **kwargs):

        metadata_tags = LegacyRole.objects.all().values_list("full_metadata__tags", flat=True)
        tag_list = list(chain(*metadata_tags))

        tags = [dict(name=tag, count=tag_list.count(tag)) for tag in set(tag_list)]

        tags = self._filter_queryset(tags, request)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(tags, request, view=self)

        return paginator.get_paginated_response(page)
