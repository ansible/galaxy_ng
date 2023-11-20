from django.db.models import Q
from django.db.models import Case, Value, When
from django_filters import filters
from django_filters.rest_framework import filterset

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.api.v1.models import LegacyRoleImport
from galaxy_ng.app.utils.rbac import get_v3_namespace_owners


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
