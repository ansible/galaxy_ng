from rest_framework.response import Response

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api import permissions
from galaxy_ng.app.api.ui import serializers


class CurrentUserViewSet(api_base.GenericViewSet):
    serializer_class = serializers.CurrentUserSerializer

    def retrieve(self, request, *args, **kwargs):
        data = serializers.CurrentUserSerializer({
            'is_partner_engineer': permissions.IsPartnerEngineer().has_permission(request, self)
        }).data

        return Response(data)
