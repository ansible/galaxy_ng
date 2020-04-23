from rest_framework import mixins

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
    permission_classes = [permissions.IsPartnerEngineer]

    def get_serializer_class(self):
        return serializers.UserSerializer

    def get_queryset(self):
        return auth_models.User.objects.all()
