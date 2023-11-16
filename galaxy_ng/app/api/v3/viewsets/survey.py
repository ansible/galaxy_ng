from django.conf import settings
from django_filters import rest_framework as filters
from django.shortcuts import get_object_or_404

from rest_framework import viewsets
from rest_framework.settings import perform_import
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status

from galaxy_ng.app.api.base import LocalSettingsMixin
from galaxy_ng.app.access_control.access_policy import SurveyAccessPolicy
from galaxy_ng.app.utils.survey import calculate_survey_score


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

from galaxy_ng.app.api.v1.models import (
    LegacyRole
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


class LegacyRoleSurveyList(LocalSettingsMixin, viewsets.ModelViewSet):
    queryset = LegacyRoleSurvey.objects.all()
    serializer_class = LegacyRoleSurveySerializer

    permission_classes = [SurveyAccessPolicy]

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = LegacyRoleSurveyFilter

    def get_queryset(self):
        return LegacyRoleSurvey.objects.filter(
            user=self.request.user
        )

    def create(self, *args, **kwargs):
        print(f'ARGS:{args} KWARGS:{kwargs}')
        role_id = kwargs.get('id')

        if not role_id:
            return Response(
                {"message": "role id not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        role = get_object_or_404(LegacyRole, id=role_id)

        defaults = self.request.data

        survey, _ = LegacyRoleSurvey.objects.get_or_create(
            user=self.request.user,
            role=role,
            defaults=defaults
        )

        # re-compute score ...
        new_score = calculate_survey_score(LegacyRoleSurvey.objects.filter(role=role))
        score,_ = LegacyRoleSurveyRollup.objects.get_or_create(
            role=role,
            defaults={'score': new_score}
        )
        if score.score != new_score:
            score.score = new_score
            score.save()

        return Response({'id': survey.id}, status=status.HTTP_201_CREATED)
