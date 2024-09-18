from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework import mixins
from rest_framework import views

from ansible_base.rest_pagination.default_paginator import DefaultPaginator

from .filters import UserViewFilter
from .filters import GroupViewFilter
from .filters import OrganizationFilter
from .filters import TeamFilter
from .serializers import UserDetailSerializer
from .serializers import UserCreateUpdateDeleteSerializer
from .serializers import GroupSerializer
from .serializers import OrganizationSerializer
from .serializers import TeamSerializer
from .permissions import IsSuperUserOrReadOnly
from .permissions import ComplexUserPermissions

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


class CurrentUserViewSet(
    BaseViewSet,
    mixins.RetrieveModelMixin,
):
    serializer_class = UserDetailSerializer
    model = User

    def get_object(self):
        return self.request.user


class UserViewSet(BaseViewSet):
    queryset = User.objects.all().order_by('id')
    filterset_class = UserViewFilter
    permission_classes = [ComplexUserPermissions]

    def get_serializer_class(self):
        # FIXME - a single serializer for this viewset
        #         seems painful to implement.
        if self.action in ['list', 'retrieve']:
            return UserDetailSerializer
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return UserCreateUpdateDeleteSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save the user, which internally handles group assignment
        user = serializer.save()

        # Return the created user data (excluding sensitive fields like password)
        return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserDetailSerializer(user).data, status=status.HTTP_200_OK)

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
