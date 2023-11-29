from django.db.models import Q
from django_filters import filters
from django_filters.rest_framework import filterset

from galaxy_ng.app.api.v1.models import LegacyRoleSurvey
from galaxy_ng.app.api.v1.models import CollectionSurvey


class BaseSurveyFilter(filterset.FilterSet):

    user = filters.CharFilter(method='user_filter')

    sort = filters.OrderingFilter(
        fields=(
            ('created', 'created'),
        )
    )

    def user_filter(self, queryset, name, value):

        # allow filtering on uid and username ...
        if value.isdigit():
            queryset = queryset.filter(
                Q(user__id=int(value)) | Q(user__username=value)
            )
        else:
            queryset = queryset.filter(user__username=value)

        return queryset


class LegacyRoleSurveyFilter(BaseSurveyFilter):

    role = filters.CharFilter(method='role_filter')

    class Meta:
        model = LegacyRoleSurvey
        fields = ['created', 'user', 'role']

    def role_filter(self, queryset, name, value):
        return queryset.filter(role__id=int(value))


class CollectionSurveyFilter(BaseSurveyFilter):

    collection = filters.CharFilter(method='collection_filter')

    class Meta:
        model = CollectionSurvey
        fields = ['created', 'user', 'collection']

    def collection_filter(self, queryset, name, value):
        return queryset.filter(collection__pulp_id=value)
