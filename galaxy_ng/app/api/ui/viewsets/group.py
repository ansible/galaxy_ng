import logging

from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend

from rest_framework import mixins

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.ui import serializers
from galaxy_ng.app.api import base as api_base


log = logging.getLogger(__name__)


class GroupFilter(filterset.FilterSet):
    sort = filters.OrderingFilter(
        fields=(
            ('name', 'name'),
        )
    )

    class Meta:
        model = auth_models.Group
        fields = {
            'name': ['exact', 'contains']
        }


class GroupViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    api_base.GenericViewSet,
):
    serializer_class = serializers.GroupSerializer
    model = auth_models.Group
    queryset = auth_models.Group.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = GroupFilter
    permission_classes = [access_policy.GroupAccessPolicy]
