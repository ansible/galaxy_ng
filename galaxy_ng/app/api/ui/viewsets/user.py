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
    permission_classes = [
        permissions.IsPartnerEngineer,
        permissions.RestrictOnCloudDeployments]

    def get_serializer_class(self):
        return serializers.UserSerializer

    def get_queryset(self):
        return auth_models.User.objects.all()


class CurrentUserViewSet(
    api_base.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
):
    serializer_class = serializers.CurrentUserSerializer
    model = auth_models.User
    permission_classes = [
        drf_permissions.IsAuthenticated,
        permissions.RestrictUnsafeOnCloudDeployments]

    def get_object(self):
        obj, created = self.model.objects.get_or_create(
            pk=self.request.user.pk
        )
        return obj
