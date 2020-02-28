from rest_framework import viewsets
from rest_framework.response import Response

from pulp_galaxy.app.api import permissions
from pulp_galaxy.app.api.ui import serializers


class CurrentUserViewSet(viewsets.GenericViewSet):
    def retrieve(self, request, *args, **kwargs):
        data = serializers.CurrentUserSerializer({
            'is_partner_engineer': permissions.IsPartnerEngineer().has_permission(request, self)
        }).data

        return Response(data)
