from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action

from ansible_base.rest_pagination.default_paginator import DefaultPaginator

from .filters import UserViewFilter
from .filters import GroupViewFilter
from .filters import OrganizationFilter
from .filters import TeamFilter
from .serializers import UserSerializer
from .serializers import GroupSerializer
from .serializers import OrganizationSerializer
from .serializers import TeamSerializer
from .permissions import IsSuperUserOrReadOnly

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.models.auth import Group
from galaxy_ng.app.models.organization import Organization
from galaxy_ng.app.models.organization import Team


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = UserViewFilter
    pagination_class = DefaultPaginator
    permission_classes = [IsSuperUserOrReadOnly]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        password = serializer.validated_data.get('password')
        if password:
            user = User(
                email=serializer.validated_data['email'],
                username=serializer.validated_data['username']
            )
            user.set_password(password)
            user.save()
            serializer.instance = user
        else:
            serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    def perform_update(self, serializer):
        password = serializer.validated_data.get('password')
        if password:
            serializer.instance.set_password(password)
            serializer.instance.save()
        serializer.save()


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Group.objects.all().order_by('id')
    serializer_class = GroupSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = GroupViewFilter
    pagination_class = DefaultPaginator
    permission_classes = [IsSuperUserOrReadOnly]


class OrganizationViewSet(viewsets.ModelViewSet):

    queryset = Organization.objects.all().order_by('pk')
    serializer_class = OrganizationSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = OrganizationFilter
    pagination_class = DefaultPaginator
    permission_classes = [IsSuperUserOrReadOnly]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.name == "Default" and request.data.get('name') != "Default":
            raise ValidationError("The name 'Default' cannot be changed.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.name == "Default":
            raise ValidationError("'Default' organization cannot be deleted.")

        return super().destroy(request, *args, **kwargs)


class TeamViewSet(viewsets.ModelViewSet):

    queryset = Team.objects.all().order_by('id')
    serializer_class = TeamSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TeamFilter
    pagination_class = DefaultPaginator
    permission_classes = [IsSuperUserOrReadOnly]

    def create(self, request, *args, **kwargs):

        # make the organization ...
        org_name = request.data.get('organization', 'Default')
        organization, _ = Organization.objects.get_or_create(
            name=org_name
        )

        # make the team ...
        team, created = Team.objects.get_or_create(
            name=request.data['name'],
            defaults={'organization': organization}
        )
        if not created:
            raise ValidationError("A team with this name already exists.")

        # set the group name ...
        group_name = organization.name + '::' + team.name
        team.group.name = group_name
        team.group.save()

        serializer = self.serializer_class(team)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='users/associate')
    def associate_users(self, request, pk=None):
        team = self.get_object()
        user_ids = request.data.get('instances', [])

        if not user_ids:
            return Response({"detail": "No user IDs provided."}, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(id__in=user_ids)

        for user in users:
            team.users.add(user)
            team.group.user_set.add(user)

        return Response({"detail": "Users associated successfully."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='users/disassociate')
    def disassociate_users(self, request, pk=None):
        team = self.get_object()
        user_ids = request.data.get('instances', [])

        # Ensure the user_ids list is not empty
        if not user_ids:
            return Response({"detail": "No user IDs provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the users to be disassociated
        users = User.objects.filter(id__in=user_ids)

        # Disassociate users from the team
        for user in users:
            team.users.remove(user)
            team.group.user_set.remove(user)

        return Response({"detail": "Users disassociated successfully."}, status=status.HTTP_200_OK)
