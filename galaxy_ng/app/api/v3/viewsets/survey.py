from django.conf import settings
from django_filters import rest_framework as filters
from rest_framework import viewsets

from galaxy_ng.app.access_control.access_policy import SurveyAccessPolicy

from rest_framework.settings import perform_import
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from galaxy_ng.app.models import (
    CollectionSurvey,
    CollectionSurveyRollup,
    LegacyRoleSurveyRollup,
    LegacyRoleSurvey,
)

from galaxy_ng.app.api.v3.serializers import (
    CollectionSurveyRollupSerializer,
    CollectionSurveySerializer,
    LegacyRoleSurveyRollupSerializer,
    LegacyRoleSurveySerializer,
)

from galaxy_ng.app.api.v3.filtersets import (
    CollectionSurveyFilter,
    LegacyRoleSurveyFilter,
)


GALAXY_AUTHENTICATION_CLASSES = perform_import(
    settings.GALAXY_AUTHENTICATION_CLASSES,
    'GALAXY_AUTHENTICATION_CLASSES'
)


class CollectionSurveyRollupList(viewsets.ModelViewSet):
    queryset = CollectionSurveyRollup.objects.all()
    serializer_class = CollectionSurveyRollupSerializer

    # access_policy.py is lame.
    permission_classes = [IsAuthenticatedOrReadOnly]


class LegacyRoleSurveyRollupList(viewsets.ModelViewSet):
    queryset = LegacyRoleSurveyRollup.objects.all()
    serializer_class = LegacyRoleSurveyRollupSerializer

    # access_policy.py is lame.
    permission_classes = [IsAuthenticatedOrReadOnly]


class CollectionSurveyList(viewsets.ModelViewSet):
    queryset = CollectionSurvey.objects.all()
    serializer_class = CollectionSurveySerializer

    permission_classes = [SurveyAccessPolicy]

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = CollectionSurveyFilter

    def get_queryset(self):
        return CollectionSurvey.objects.filter(
            user=self.request.user
        )


class LegacyRoleSurveyList(viewsets.ModelViewSet):
    queryset = LegacyRoleSurvey.objects.all()
    serializer_class = LegacyRoleSurveySerializer

    permission_classes = [SurveyAccessPolicy]

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = LegacyRoleSurveyFilter

    def get_queryset(self):
        return LegacyRoleSurvey.objects.filter(
            user=self.request.user
        )
