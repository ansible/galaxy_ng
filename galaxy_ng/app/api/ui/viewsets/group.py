from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend

from pulpcore.app import viewsets
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app.api.base import LocalSettingsMixin
from django.contrib.auth.models import Group


class GroupFilter(filterset.FilterSet):
    sort = filters.OrderingFilter(
        fields=(
            ('name', 'name'),
        )
    )

    class Meta:
        model = Group
        fields = {
            'name': ['exact', 'contains', 'startswith']
        }


class GroupViewSet(LocalSettingsMixin, viewsets.GroupViewSet):
    filter_backends = (DjangoFilterBackend,)
    filterset_class = GroupFilter
    permission_classes = [access_policy.GroupAccessPolicy]


class GroupModelPermissionViewSet(LocalSettingsMixin, viewsets.GroupModelPermissionViewSet):
    permission_classes = [access_policy.GroupAccessPolicy]


class GroupUserViewSet(LocalSettingsMixin, viewsets.GroupUserViewSet):
    permission_classes = [access_policy.GroupAccessPolicy]
