from django.db.models import Q
from django.db.models import Case, Value, When
from django_filters import filters
from django_filters.rest_framework import filterset

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.api.v1.models import LegacyRoleImport
from galaxy_ng.app.utils.rbac import get_v3_namespace_owners


class LegacyNamespaceFilter(filterset.FilterSet):

    keywords = filters.CharFilter(method='keywords_filter')
    owner = filters.CharFilter(method='owner_filter')

    sort = filters.OrderingFilter(
        fields=(
            ('created', 'created'),
            ('name', 'name')
        )
    )

    class Meta:
        model = LegacyNamespace
        fields = ['created', 'name']

    def keywords_filter(self, queryset, name, value):

        keywords = self.request.query_params.getlist('keywords')

        for keyword in keywords:
            queryset = queryset.filter(Q(name__icontains=keyword))

        return queryset

    def owner_filter(self, queryset, name, value):
        # find the owner on the linked v3 namespace

        # FIXME - this is terribly slow
        pks = []
        for ns1 in LegacyNamespace.objects.all():
            if not ns1.namespace:
                continue
            ns3 = ns1.namespace
            owners = get_v3_namespace_owners(ns3)
            if value in [x.username for x in owners]:
                pks.append(ns1.id)

        queryset = queryset.filter(id__in=pks)

        return queryset
