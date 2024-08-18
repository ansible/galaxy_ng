from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework import views

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


class BaseView(views.APIView):
    """
    A view to define the base properties for the views in
    ansible_base.rbac. Set ANSIBLE_BASE_CUSTOM_VIEW_PARENT
    to this class in settings so that the rbac endpoints
    follow the defined pagination and permission classes.
    """
    pagination_class = DefaultPaginator
    permission_classes = [IsSuperUserOrReadOnly]

    # openapi compatibility ...
    def endpoint_pieces(*args, **kwargs):
        return ''


class BaseViewSet(viewsets.ModelViewSet):
    filter_backends = (DjangoFilterBackend,)
    pagination_class = DefaultPaginator
    permission_classes = [IsSuperUserOrReadOnly]


class UserViewSet(BaseViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    filterset_class = UserViewFilter

    '''
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    '''

    def perform_create(self, serializer):

        '''
        password = serializer.validated_data.get('password')
        if password:

            # can't get_or_create with groups/teams/orgs ...
            validated_data = copy.deepcopy(serializer.validated_data)
            groups = validated_data.pop('groups', None)
            teams = validated_data.pop('teams', None)
            orgs = validated_data.pop('organizations', None)

            user, _ = User.objects.get_or_create(
                username=validated_data['username'],
                defaults=validated_data
            )
            user.set_password(password)
            user.save()
            serializer.instance = user
        else:
            serializer.save()
        '''

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


class GroupViewSet(BaseViewSet):
    queryset = Group.objects.all().order_by('id')
    serializer_class = GroupSerializer
    filterset_class = GroupViewFilter


class OrganizationViewSet(BaseViewSet):

    queryset = Organization.objects.all().order_by('pk')
    serializer_class = OrganizationSerializer
    filterset_class = OrganizationFilter

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


class TeamViewSet(BaseViewSet):

    queryset = Team.objects.all().order_by('id')
    serializer_class = TeamSerializer
    filterset_class = TeamFilter

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
