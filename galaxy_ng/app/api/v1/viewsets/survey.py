from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django_filters import rest_framework as filters
from django.shortcuts import get_object_or_404

from rest_framework import viewsets
from rest_framework.settings import perform_import
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from galaxy_ng.app.access_control.access_policy import SurveyAccessPolicy
from galaxy_ng.app.api.v1.utils_survey import calculate_survey_score


from galaxy_ng.app.api.v1.models import (
    CollectionSurvey,
    CollectionSurveyRollup,
    LegacyRoleSurveyRollup,
    LegacyRoleSurvey,
    LegacyRole
)

from galaxy_ng.app.api.v1.serializers_survey import (
    CollectionSurveyRollupSerializer,
    CollectionSurveySerializer,
    LegacyRoleSurveyRollupSerializer,
    LegacyRoleSurveySerializer,
)

from galaxy_ng.app.api.v1.filtersets_survey import (
    CollectionSurveyFilter,
    LegacyRoleSurveyFilter,
)

from galaxy_ng.app.api.v1.filtersets_scores import (
    CollectionSurveyRollupFilter,
    LegacyRoleSurveyRollupFilter,
)

from pulp_ansible.app.models import Collection


GALAXY_AUTHENTICATION_CLASSES = perform_import(
    settings.GALAXY_AUTHENTICATION_CLASSES,
    'GALAXY_AUTHENTICATION_CLASSES'
)


class SurveyPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000


class CollectionSurveyRollupList(viewsets.ModelViewSet):
    queryset = CollectionSurveyRollup.objects.all().order_by('created')
    serializer_class = CollectionSurveyRollupSerializer
    pagination_class = SurveyPagination

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = CollectionSurveyRollupFilter

    # access_policy.py is lame.
    permission_classes = [IsAuthenticatedOrReadOnly]

    def retrieve_collection(self, *args, **kwargs):
        """Get the score object by namespace/name path."""

        print(f'PAGINATION: {self.pagination_class}')

        namespace = kwargs['namespace']
        name = kwargs['name']

        collection = get_object_or_404(Collection, namespace=namespace, name=name)
        score = get_object_or_404(CollectionSurveyRollup, collection=collection)

        serializer = CollectionSurveyRollupSerializer(score)
        data = serializer.data

        resp = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [data]
        }

        # return Response(serializer.data)
        # return self.get_paginated_response(serializer.data)
        return Response(resp)


class LegacyRoleSurveyRollupList(viewsets.ModelViewSet):
    queryset = LegacyRoleSurveyRollup.objects.all().order_by('created')
    serializer_class = LegacyRoleSurveyRollupSerializer
    pagination_class = SurveyPagination

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = LegacyRoleSurveyRollupFilter

    # access_policy.py is lame.
    permission_classes = [IsAuthenticatedOrReadOnly]


class CollectionSurveyList(viewsets.ModelViewSet):
    queryset = CollectionSurvey.objects.all().order_by('created')
    serializer_class = CollectionSurveySerializer
    pagination_class = SurveyPagination

    permission_classes = [SurveyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = CollectionSurveyFilter

    def get_queryset(self):

        # Anonymous users shouldn't see anyone's survey responses
        # The access policy should prevent this code from executing,
        # but we'll have it just in case.
        if isinstance(self.request.user, AnonymousUser):
            return CollectionSurvey.objects.none()

        return CollectionSurvey.objects.filter(
            user=self.request.user
        )

    def create(self, *args, **kwargs):
        # the collection serializer doesn't include an ID,
        # so all we have to go by is namespace.name ...
        namespace = kwargs.get('namespace')
        name = kwargs.get('name')

        if not namespace or not name:
            return Response(
                {"message": f"{namespace}.{name} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        collection = get_object_or_404(Collection, namespace=namespace, name=name)

        defaults = self.request.data

        survey, _ = CollectionSurvey.objects.get_or_create(
            user=self.request.user,
            collection=collection,
            defaults=defaults
        )

        # re-compute score ...
        new_score = calculate_survey_score(CollectionSurvey.objects.filter(collection=collection))
        score, _ = CollectionSurveyRollup.objects.get_or_create(
            collection=collection,
            defaults={'score': new_score}
        )
        if score.score != new_score:
            score.score = new_score
            score.save()

        return Response({'id': survey.id}, status=status.HTTP_201_CREATED)


class LegacyRoleSurveyList(viewsets.ModelViewSet):
    queryset = LegacyRoleSurvey.objects.all().order_by('created')
    serializer_class = LegacyRoleSurveySerializer
    pagination_class = SurveyPagination

    permission_classes = [SurveyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = LegacyRoleSurveyFilter

    def get_queryset(self):

        # Anonymous users shouldn't see anyone's survey responses
        # The access policy should prevent this code from executing,
        # but we'll have it just in case.
        if isinstance(self.request.user, AnonymousUser):
            return LegacyRoleSurvey.objects.none()

        return LegacyRoleSurvey.objects.filter(
            user=self.request.user
        )

    def create(self, *args, **kwargs):
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
        score, _ = LegacyRoleSurveyRollup.objects.get_or_create(
            role=role,
            defaults={'score': new_score}
        )
        if score.score != new_score:
            score.score = new_score
            score.save()

        return Response({'id': survey.id}, status=status.HTTP_201_CREATED)
