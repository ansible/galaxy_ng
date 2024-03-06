from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui.serializers.organization import (
    OrganizationRepositorySerializer,
    OrganizationRepositoryCreateSerializer,
)


class OrganizationRepositoryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    api_base.GenericViewSet
):
    permission_classes = [access_policy.OrganizationResourceAccessPolicy]
    lookup_field = 'repository_id'

    def get_queryset(self):
        org_id = self.kwargs["organization_id"]
        org_exists = models.Organization.objects.filter(id=org_id).exists()
        if not org_exists:
            raise NotFound(_("Organization {} does not exist.").format(org_id))
        return models.OrganizationRepository.objects.filter(organization_id=org_id)

    def get_serializer_class(self):
        if self.action == "create":
            return OrganizationRepositoryCreateSerializer
        return OrganizationRepositorySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data={
            "repository": self.kwargs["repository_id"],
            "organization": self.kwargs["organization_id"],
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
