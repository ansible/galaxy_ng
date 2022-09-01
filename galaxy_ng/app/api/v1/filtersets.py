from django.db.models import Q
from django_filters import filters
from django_filters.rest_framework import filterset

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole


class LegacyNamespaceFilter(filterset.FilterSet):

    keywords = filters.CharFilter(method='keywords_filter')

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
        return queryset.filter(name=username)


class LegacyRoleFilter(filterset.FilterSet):

    github_user = filters.CharFilter(method='github_user_filter')
    keywords = filters.CharFilter(method='keywords_filter')

    sort = filters.OrderingFilter(
        fields=(
            ('created', 'full_metadata__created'),
            # ('name', 'name')
        )
    )

    class Meta:
        model = LegacyRole
        fields = ['created', 'name']

    def github_user_filter(self, queryset, name, value):
        return queryset.filter(namespace__name=value)

    def keywords_filter(self, queryset, name, value):

        keywords = self.request.query_params.getlist('keywords')

        for keyword in keywords:
            queryset = queryset.filter(
                Q(namespace__name__contains=keyword)
                | Q(name__contains=keyword)
                | Q(full_metadata__description__contains=keyword)
            )

        return queryset
