from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend

from pulpcore.app import viewsets
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app.api.base import LocalSettingsMixin
from galaxy_ng.app.exceptions import ConflictError
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
            'name': ['exact', 'contains', 'icontains', 'startswith']
        }


class GroupViewSet(LocalSettingsMixin, viewsets.GroupViewSet):
    filter_backends = (DjangoFilterBackend,)
    filterset_class = GroupFilter
    permission_classes = [access_policy.GroupAccessPolicy]
    queryset = Group.objects.all()

    # TODO(awcrosby): replace this by setting attribute to None
    # after https://pulp.plan.io/issues/8438 is resolved
    def _remove_attr(self):
        raise AttributeError
    queryset_filtering_required_permission = property(_remove_attr)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        name = request.data['name']
        if Group.objects.filter(name=name).exists():
            raise ConflictError(
                detail={'name': _('A group named %s already exists.') % name}
            )
        return super().create(request, *args, **kwargs)


class GroupUserViewSet(LocalSettingsMixin, viewsets.GroupUserViewSet):
    permission_classes = [access_policy.GroupAccessPolicy]
