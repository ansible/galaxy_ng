from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import filters
from django_filters.rest_framework import DjangoFilterBackend, filterset
from pulp_ansible.app.models import Collection
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from galaxy_ng.app import models
from galaxy_ng.app.access_control.access_policy import NamespaceAccessPolicy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.v3 import serializers
from galaxy_ng.app.exceptions import ConflictError
from galaxy_ng.app.models.namespace import delete_inbound_repo


class NamespaceFilter(filterset.FilterSet):
    keywords = filters.CharFilter(method='keywords_filter')

    sort = filters.OrderingFilter(
        fields=(
            ('name', 'name'),
            ('company', 'company'),
            ('id', 'id'),
        ),
    )

    class Meta:
        model = models.Namespace
        fields = ('name', 'company',)

    def keywords_filter(self, queryset, name, value):

        keywords = self.request.query_params.getlist('keywords')

        for keyword in keywords:
            queryset = queryset.filter(Q(name__icontains=keyword) | Q(company__icontains=keyword))

        return queryset


class NamespaceViewSet(api_base.ModelViewSet):
    lookup_field = "name"
    queryset = models.Namespace.objects.all()
    serializer_class = serializers.NamespaceSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = NamespaceFilter
    swagger_schema = None
    permission_classes = [NamespaceAccessPolicy]

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.NamespaceSummarySerializer
        else:
            return self.serializer_class

    @transaction.atomic
    def create(self, request: Request, *args, **kwargs) -> Response:
        """Override to validate for name duplication before serializer validation."""
        name = request.data.get('name')
        if name and models.Namespace.objects.filter(name=name).exists():
            # Ensures error raised is 409, not 400.
            raise ConflictError(
                detail={'name': _('A namespace named %s already exists.') % name}
            )
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Delete a namespace.

        1. Perform a check to see if there are any collections in the namespace.
           If there are, return a failure.
        2. Delete the inbound pulp distro and repository
        3. Delete the namespace object.

        return: Response(status=204)
        """
        namespace = self.get_object()

        # 1. Check if there are any collections in the namespace.
        if Collection.objects.filter(namespace=namespace.name).exists():
            raise ValidationError(
                detail=_(
                    "Namespace {name} cannot be deleted because "
                    "there are still collections associated with it."
                ).format(name=namespace.name)
            )

        # 2. Delete the inbound pulp distro and repository
        #    the Namespace model delete will handle this but
        #    was kept here for better clarity.
        delete_inbound_repo(namespace.name)

        # 3. Delete the namespace object.
        self.perform_destroy(namespace)

        return Response(status=status.HTTP_204_NO_CONTENT)
