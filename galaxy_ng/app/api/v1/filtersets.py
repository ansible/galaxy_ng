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
    provider = filters.CharFilter(method='provider_filter')

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

    def provider_filter(self, queryset, name, value):
        return queryset.filter(namespace__name=value)


class LegacyUserFilter(filterset.FilterSet):

    username = filters.CharFilter(method='username_filter')

    sort = filters.OrderingFilter(
        fields=(
            # ('created', 'created'),
            ('username', 'username')
        )
    )

    class Meta:
        model = User
        # fields = ['created', 'username']
        fields = ['username']

    def username_filter(self, queryset, name, value):
        username = self.request.query_params.get('username')
        return queryset.filter(username=username)


class LegacyRoleFilterOrdering(filters.OrderingFilter):
    def filter(self, qs, value):
        if value is not None and any(v in ["download_count", "-download_count"] for v in value):
            order = "-" if "-download_count" in value else ""

            return qs.annotate(
                download_count=Case(
                    When(legacyroledownloadcount=None, then=Value(0)),
                    default="legacyroledownloadcount__count",
                )
            ).order_by(f"{order}download_count")

        return super().filter(qs, value)


class LegacyRoleFilter(filterset.FilterSet):

    github_user = filters.CharFilter(method='github_user_filter')
    keywords = filters.CharFilter(method='keywords_filter')
    tags = filters.CharFilter(method='tags_filter')
    tag = filters.CharFilter(method='tags_filter')
    autocomplete = filters.CharFilter(method='autocomplete_filter')
    username_autocomplete = filters.CharFilter(method='username_autocomplete_filter')
    owner__username = filters.CharFilter(method='owner__username_filter')
    namespace = filters.CharFilter(method='namespace_filter')

    order_by = LegacyRoleFilterOrdering(
        fields=(
            ('name', 'name'),
            ('created', 'created'),
            ('modified', 'modified'),
            ('download_count', 'download_count')
        )
    )

    class Meta:
        model = LegacyRole
        fields = ['created', 'name', "modified"]

    def github_user_filter(self, queryset, name, value):
        return queryset.filter(namespace__name=value)

    def namespace_filter(self, queryset, name, value):
        return queryset.filter(namespace__name__iexact=value)

    def owner__username_filter(self, queryset, name, value):
        """
        The cli uses this filter to find a role by the namespace.
        It should be case insenstive such that Foo and foo find
        the same content... hence the __iexact
        """
        return queryset.filter(namespace__name__iexact=value)

    def tags_filter(self, queryset, name, value):

        queryset = queryset.filter(Q(full_metadata__tags__contains=value))

        return queryset

    def keywords_filter(self, queryset, name, value):

        keywords = self.request.query_params.getlist('keywords')

        for keyword in keywords:
            queryset = queryset.filter(
                Q(namespace__name__contains=keyword)
                | Q(name__contains=keyword)
                | Q(full_metadata__description__contains=keyword)
            )

        return queryset

    def autocomplete_filter(self, queryset, name, value):

        keywords = self.request.query_params.getlist('autocomplete')

        for keyword in keywords:
            queryset = queryset.filter(
                Q(namespace__name__contains=keyword)
                | Q(name__contains=keyword)
                | Q(full_metadata__description__contains=keyword)
            )

        return queryset

    def username_autocomplete_filter(self, queryset, name, value):

        keywords = self.request.query_params.getlist('username_autocomplete')

        for keyword in keywords:
            queryset = queryset.filter(namespace__name__icontains=keyword)

        return queryset


class LegacyRoleImportFilter(filterset.FilterSet):
    """
    Filter legacy role imports.

    Used by the UI to find the last import log by role id.
    """

    order_by = filters.OrderingFilter(
        fields=(
            ('task__pulp_created', 'created'),
        )
    )

    role_id = filters.NumberFilter(field_name='role__id')
    role_name = filters.NumberFilter(field_name='role__name')
    namespace_id = filters.NumberFilter(field_name='role__namespace_id')
    namespace_name = filters.NumberFilter(field_name='role__namespace_name')
    github_user = filters.CharFilter(field_name='task__kwargs__github_user')
    github_repo = filters.CharFilter(field_name='task__kwargs__github_repo')
    state = filters.CharFilter(method='state_filter')

    class Meta:
        model = LegacyRoleImport
        fields = [
            'role_id',
            'role_name',
            'namespace_id',
            'namespace_name',
            'github_user',
            'github_repo',
            'state'
        ]

    def state_filter(self, queryset, name, value):
        if value.lower() == 'success':
            value = 'completed'
        return queryset.filter(task__state=value.lower())
