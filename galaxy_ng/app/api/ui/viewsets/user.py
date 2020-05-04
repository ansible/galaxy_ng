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

    def get_serializer_class(self):
        return serializers.UserSerializer

    def get_queryset(self):
        return auth_models.User.objects.all()

    def get_permissions(self):
        permission_list = super().get_permissions()
        permission_list.append(permissions.IsPartnerEngineer())
        permission_list.append(permissions.RestrictOnCloudDeployments())
        return permission_list


class CurrentUserViewSet(
    api_base.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
):
    serializer_class = serializers.CurrentUserSerializer
    model = auth_models.User

    def get_permissions(self):
        permission_list = super().get_permissions()
        permission_list.append(drf_permissions.IsAuthenticated())
        permission_list.append(permissions.RestrictUnsafeOnCloudDeployments())
        return permission_list

    def get_object(self):
        obj = get_object_or_404(self.model, pk=self.request.user.pk)
        return obj
