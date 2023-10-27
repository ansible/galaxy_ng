import logging

from django.conf import settings
from django.db import transaction
from django.db.utils import InternalError as DatabaseInternalError
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from rest_framework import mixins
from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.settings import perform_import
from rest_framework.pagination import PageNumberPagination

from galaxy_ng.app.access_control.access_policy import LegacyAccessPolicy

from galaxy_ng.app.api.v1.tasks import (
    legacy_role_import,
)
from galaxy_ng.app.api.v1.models import (
    LegacyRole,
    LegacyRoleDownloadCount,
)
from galaxy_ng.app.api.v1.serializers import (
    LegacyImportSerializer,
    LegacyRoleSerializer,
    LegacyRoleUpdateSerializer,
    LegacyRoleContentSerializer,
    LegacyRoleVersionsSerializer,
)

from galaxy_ng.app.api.v1.viewsets.tasks import LegacyTasksMixin
from galaxy_ng.app.api.v1.filtersets import LegacyRoleFilter


GALAXY_AUTHENTICATION_CLASSES = perform_import(
    settings.GALAXY_AUTHENTICATION_CLASSES,
    'GALAXY_AUTHENTICATION_CLASSES'
)

logger = logging.getLogger(__name__)


class LegacyRolesSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyRolesViewSet(viewsets.ModelViewSet):
    """A list of legacy roles."""

    queryset = LegacyRole.objects.all().order_by('created')
    ordering = ('created')
    filter_backends = (DjangoFilterBackend,)
    filterset_class = LegacyRoleFilter

    serializer_class = LegacyRoleSerializer
    pagination_class = LegacyRolesSetPagination

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    def list(self, request):

        # this is the naive logic used in the original galaxy to assume a role
        # was being downloaded by the CLI...
        if request.query_params.get('owner__username') and request.query_params.get('name'):

            role_namespace = request.query_params.get('owner__username')
            role_name = request.query_params.get('name')
            role = LegacyRole.objects.filter(namespace__name=role_namespace, name=role_name).first()
            if role:

                with transaction.atomic():

                    try:
                        # attempt to get or create the counter first
                        counter, _ = LegacyRoleDownloadCount.objects.get_or_create(legacyrole=role)

                        # now lock the row so that we avoid race conditions
                        counter = LegacyRoleDownloadCount.objects.select_for_update().get(
                            pk=counter.pk
                        )

                        # increment and save
                        counter.count += 1
                        counter.save()
                    except DatabaseInternalError as e:
                        # Fail gracefully if the database is in read-only mode.
                        if "read-only" in str(e):
                            pass
                        else:
                            raise e

        return super().list(request)

    def update(self, request, pk=None):
        role = self.get_object()
        serializer = LegacyRoleUpdateSerializer(role, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        changed = {}
        for key, newval in serializer.validated_data.items():

            # repositories are special ...
            if key == 'repository':
                if not role.full_metadata.get('repository'):
                    changed['repository'] = {}
                    role.full_metadata['repository'] = {}
                for subkey, subval in newval.items():
                    print(f'{key}.{subkey} {role.full_metadata[key].get(subkey)} --> {subval}')
                    if role.full_metadata.get(key, {}).get(subkey) != subval:
                        if key not in changed:
                            changed[key] = {}
                        role.full_metadata[key][subkey] = subval
                        changed[key][subkey] = subval
                continue

            print(f'{key} {role.full_metadata.get(key)} --> {newval}')
            if role.full_metadata.get(key) != newval:
                role.full_metadata[key] = newval
                changed[key] = newval

            # TODO - get rid of github_reference?
            if key == 'github_branch':
                key = 'github_reference'
                if role.full_metadata.get(key) != newval:
                    role.full_metadata[key] = newval
                    changed[key] = newval

        # only save if changes made
        if changed:
            role.save()
            return Response(changed, status=200)

        return Response(changed, status=204)

    def destroy(self, request, pk=None):
        """Delete a single role."""
        role = LegacyRole.objects.filter(id=pk).first()
        role.delete()
        return Response({'status': 'ok'}, status=204)

    def delete_by_url_params(self, request):
        github_user = request.query_params.get('github_user')
        github_repo = request.query_params.get('github_repo')

        qs = LegacyRole.objects
        qs = qs.filter(namespace__name=github_user)
        qs = qs.filter(full_metadata__github_repo=github_repo)

        if qs.count() == 0:
            return Response({
                'status': (
                    f'Role {github_user}.{github_repo} not found.'
                    + ' Maybe it was deleted previously?'
                ),
                'deleted_roles': []
            })

        deleted_roles = []
        for role in qs:
            role.delete()
            deleted_roles.append({
                'id': role.id,
                'namespace': role.namespace.name,
                'name': role.name,
                'github_user': github_user,
                'github_repo': github_repo,
            })

        if len(deleted_roles) == 1:
            status = f'Role {github_user}.{github_repo} deleted'
        else:
            status = (
                f'Deleted {len(deleted_roles)} roles'
                + f' associated with {github_user}/{github_repo}'
            )

        return Response({
            'status': status,
            'deleted_roles': deleted_roles,
        })


class LegacyRoleContentViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    """Documentation for a single legacy role."""

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES
    serializer_class = LegacyRoleContentSerializer

    def get_object(self):
        return get_object_or_404(LegacyRole, id=self.kwargs["pk"])


class LegacyRoleVersionsViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    """A list of versions for a single legacy role."""

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES
    serializer_class = LegacyRoleVersionsSerializer
    queryset = LegacyRole.objects.all()

    def get_object(self):
        return get_object_or_404(LegacyRole, id=self.kwargs["pk"])


class LegacyRoleImportsViewSet(viewsets.GenericViewSet, LegacyTasksMixin):
    """Legacy role imports."""

    serializer_class = LegacyImportSerializer
    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kwargs = dict(serializer.validated_data)

        # tell the defered task who started this job
        kwargs['request_username'] = request.user.username

        # synthetically create the name for the response
        role_name = kwargs.get('alternate_role_name') or \
            kwargs['github_repo'].replace('ansible-role-', '')

        task_id = self.legacy_dispatch(legacy_role_import, kwargs=kwargs)

        return Response({
            'results': [{
                'id': task_id,
                'github_user': kwargs['github_user'],
                'github_repo': kwargs['github_repo'],
                'github_reference': kwargs.get('github_reference'),
                'summary_fields': {
                    'role': {
                        'name': role_name
                    }
                }
            }]
        })
