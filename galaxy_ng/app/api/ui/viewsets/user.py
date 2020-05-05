from django.shortcuts import get_object_or_404

from rest_framework import mixins
from rest_framework import permissions as drf_permissions

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.api import permissions
from galaxy_ng.app.api.ui import serializers
from galaxy_ng.app.api import base as api_base


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    api_base.GenericViewSet,
):
    serializer_class = serializers.UserSerializer
    model = auth_models.User
    queryset = auth_models.User.objects.all()

    def get_permissions(self):
        return super().get_permissions() + [
            permissions.IsPartnerEngineer(),
            permissions.RestrictOnCloudDeployments()
        ]


class CurrentUserViewSet(
    api_base.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
):
    serializer_class = serializers.CurrentUserSerializer
    model = auth_models.User

    def get_permissions(self):
        return super().get_permissions() + [
            drf_permissions.IsAuthenticated(),
            permissions.RestrictUnsafeOnCloudDeployments()
        ]

    def get_object(self):
        return get_object_or_404(self.model, pk=self.request.user.pk)
