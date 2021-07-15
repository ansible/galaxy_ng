from django.shortcuts import get_object_or_404
from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend

from rest_framework import mixins

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.ui import serializers, versioning
from galaxy_ng.app.api import base as api_base


class UserFilter(filterset.FilterSet):
    username = filters.CharFilter(field_name='username', lookup_expr='icontains')
    email = filters.CharFilter(field_name='email', lookup_expr='icontains')
    first_name = filters.CharFilter(field_name='first_name', lookup_expr='icontains')
    last_name = filters.CharFilter(field_name='last_name', lookup_expr='icontains')
    date_joined = filters.CharFilter(field_name='date_joined')
    groups_name = filters.CharFilter(field_name='groups__name')
    groups = filters.CharFilter(field_name='groups')

    sort = filters.OrderingFilter(
        fields=(
            ('username', 'username'),
            ('email', 'email'),
            ('first_name', 'first_name'),
            ('last_name', 'last_name'),
            ('date_joined', 'date_joined')
        )
    )

    class Meta:
        model = auth_models.User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'groups__name',
            'groups',
        ]


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    api_base.GenericViewSet,
):
    serializer_class = serializers.UserSerializer
    model = auth_models.User
    queryset = auth_models.User.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = UserFilter
    permission_classes = [access_policy.UserAccessPolicy]
    versioning_class = versioning.UIVersioning


class CurrentUserViewSet(
    api_base.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
):
    serializer_class = serializers.CurrentUserSerializer
    model = auth_models.User
    permission_classes = [access_policy.MyUserAccessPolicy]
    versioning_class = versioning.UIVersioning

    def get_object(self):
        return get_object_or_404(self.model, pk=self.request.user.pk)
