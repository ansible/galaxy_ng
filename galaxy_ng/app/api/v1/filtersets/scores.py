from django_filters import filters
from django_filters.rest_framework import filterset

from galaxy_ng.app.api.v1.models import LegacyRoleSurveyRollup
from galaxy_ng.app.api.v1.models import CollectionSurveyRollup


class BaseSurveyRollupFilter(filterset.FilterSet):

    sort = filters.OrderingFilter(
        fields=(
            ('created', 'created'),
        )
    )


class LegacyRoleSurveyRollupFilter(BaseSurveyRollupFilter):

    role = filters.CharFilter(method='role_filter')
    namespace = filters.CharFilter(method='namespace_filter')
    name = filters.CharFilter(method='name_filter')

    class Meta:
        model = LegacyRoleSurveyRollup
        fields = ['created', 'role']

    def role_filter(self, queryset, name, value):
        return queryset.filter(role__id=int(value))

    def namespace_filter(self, queryset, name, value):
        return queryset.filter(role__namespace__name=value)

    def name_filter(self, queryset, name, value):
        return queryset.filter(role__name=value)


class CollectionSurveyRollupFilter(BaseSurveyRollupFilter):

    collection = filters.CharFilter(method='collection_filter')
    namespace = filters.CharFilter(method='namespace_filter')
    name = filters.CharFilter(method='name_filter')

    class Meta:
        model = CollectionSurveyRollup
        fields = ['created', 'collection']

    def collection_filter(self, queryset, name, value):
        return queryset.filter(collection__pulp_id=value)

    def namespace_filter(self, queryset, name, value):
        return queryset.filter(collection__namespace=value)

    def name_filter(self, queryset, name, value):
        return queryset.filter(collection__name=value)
