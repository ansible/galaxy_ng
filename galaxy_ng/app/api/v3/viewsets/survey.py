from rest_framework import viewsets

from galaxy_ng.app.models import (
    CollectionSurveyRollup,
    LegacyRoleSurveyRollup,
)

from galaxy_ng.app.api.v3.serializers import (
    CollectionSurveyRollupSerializer,
    LegacyRoleSurveyRollupSerializer,
)


class CollectionSurveyRollupList(viewsets.ModelViewSet):
    queryset = CollectionSurveyRollup.objects.all()
    serializer_class = CollectionSurveyRollupSerializer


class LegacyRoleSurveyRollupList(viewsets.ModelViewSet):
    queryset = LegacyRoleSurveyRollup.objects.all()
    serializer_class = LegacyRoleSurveyRollupSerializer
