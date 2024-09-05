from django.db.models import Count
from rest_framework import mixins
from django_filters import filters
from django_filters.rest_framework import DjangoFilterBackend, filterset

from pulp_ansible.app.models import Tag
from pulp_ansible.app.serializers import TagSerializer

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui import versioning
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.v1.models import LegacyRoleTag
from galaxy_ng.app.api.v1.serializers import LegacyRoleTagSerializer


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


class CollectionTagFilterOrdering(filters.OrderingFilter):
    def filter(self, qs, value):
        if value is not None and any(v in ["count", "-count"] for v in value):
            order = "-" if "-count" in value else ""

            return qs.filter(
                ansible_collectionversion__ansible_crossrepositorycollectionversionindex__is_highest=True  # noqa: E501
            ).annotate(count=Count('ansible_collectionversion')).order_by(f"{order}count")

        return super().filter(qs, value)


class CollectionTagFilter(filterset.FilterSet):
    sort = CollectionTagFilterOrdering(
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
    filterset_class = CollectionTagFilter

    queryset = Tag.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.annotate(count=Count("ansible_collectionversion"))


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
