import logging

from django.db import transaction
from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend
from pulp_ansible.app.models import AnsibleRepository, AnsibleDistribution

from galaxy_ng.app import models
from galaxy_ng.app.access_control.access_policy import NamespaceAccessPolicy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.v3 import serializers

log = logging.getLogger(__name__)

INBOUND_REPO_NAME_FORMAT = "inbound-{namespace_name}"


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
            queryset = queryset.filter(name=keyword)

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
    def create(self, request, *args, **kwargs):
        """Override to also create inbound pulp repository and distribution."""
        name = INBOUND_REPO_NAME_FORMAT.format(namespace_name=request.data['name'])
        repo = AnsibleRepository.objects.create(name=name)
        AnsibleDistribution.objects.create(name=name, base_path=name, repository=repo)
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Override to also delete inbound pulp repository and distribution.
        RepositoryVersion objects get deleted on delete of AnsibleRepository.
        """
        name = INBOUND_REPO_NAME_FORMAT.format(namespace_name=kwargs['name'])
        try:
            AnsibleRepository.objects.get(name=name).delete()
        except AnsibleRepository.DoesNotExist:
            pass
        try:
            AnsibleDistribution.objects.get(name=name).delete()
        except AnsibleDistribution.DoesNotExist:
            pass
        return super().destroy(request, *args, **kwargs)
