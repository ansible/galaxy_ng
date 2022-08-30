import logging

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse

from drf_spectacular.utils import extend_schema_field

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication
)
from rest_framework.pagination import PageNumberPagination

from galaxy_ng.app.access_control.access_policy import LegacyAccessPolicy

from galaxy_ng.app.api.v1.tasks import (
    legacy_role_import,
)
from galaxy_ng.app.api.v1.models import (
    LegacyNamespace,
    LegacyRole
)
from galaxy_ng.app.api.v1.serializers import (
    LegacyRoleSerializer,
    LegacyRoleContentSerializer,
    LegacyRoleVersionsSerializer,
)

from galaxy_ng.app.api.v1.viewsets.tasks import LegacyTasksViewset


logger = logging.getLogger(__name__)


class LegacyRolesSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyRoleBaseViewSet(viewsets.ModelViewSet, LegacyTasksViewset):
    """Base class for legacy roles."""

    queryset = LegacyRole.objects.all().order_by('full_metadata__created')
    serializer = LegacyRoleSerializer
    serializer_class = LegacyRoleSerializer
    # permission_classes = [AllowAny]
    permission_classes = [LegacyAccessPolicy]
    pagination_class = LegacyRolesSetPagination
    authentication_classes = [BasicAuthentication, SessionAuthentication, TokenAuthentication]

    def get_queryset(self):

        logger.debug(f'QUERY_PARAMS: {self.request.query_params}')

        keywords = None
        if self.request.query_params.get('keywords'):
            keywords = self.request.query_params.get('keywords').rstrip('/')

        order_by = 'full_metadata__created'
        if self.request.query_params.get('order_by'):
            order_by = self.request.query_params.get('order_by').rstrip('/')
            order_by = f'full_metadata__{order_by}'

        github_user = None
        for keyword in ['owner__username', 'github_user', 'namespace']:
            if self.request.query_params.get(keyword):
                github_user = self.request.query_params[keyword]
                if github_user is not None:
                    github_user = github_user.rstrip('/')
                break

        namespace = None
        if github_user:
            # if github_user.isdigit():
            #    namespace = LegacyNamespace.objects.filter(pk=int(github_user)).first()
            # else:
            #    namespace = LegacyNamespace.objects.filter(name=github_user).first()
            namespace = LegacyNamespace.objects.filter(name=github_user).first()

        name = self.request.query_params.get('name')
        if name is not None:
            name = name.rstrip('/')

        if github_user and name:
            logger.debug('FILTER BY USER AND NAME')
            return LegacyRole.objects.filter(namespace=namespace, name=name).order_by(order_by)

        elif github_user:
            logger.info(f'FILTER BY USER: {github_user}')
            logger.info(f'FILTER BY NAMESPACE: {namespace}')
            return LegacyRole.objects.filter(namespace=namespace).order_by(order_by)

        if keywords:
            return LegacyRole.objects.filter(
                Q(namespace__name__contains=keywords)
                | Q(name__contains=keywords)
                | Q(full_metadata__description__contains=keywords)
            ).order_by(order_by)

        # galaxy cli uses autocomplete kwargs for searching ...
        # FIXME: no support for platforms yet. More research and planning needed.
        autocomplete_kwargs = {
            'autocomplete': None,
            'platforms_autocomplete': None,
            'tags_autocomplete': None,
            'username_autocomplete': None,
        }
        for key in autocomplete_kwargs.keys():
            autocomplete_kwargs[key] = self.request.GET.get(key)
        if autocomplete_kwargs.values():
            # assemble a list of filter arguments which will be
            # an AND operation by default for each item.
            filter_args = []
            if autocomplete_kwargs['autocomplete']:
                filter_args.append(
                    Q(namespace__name__contains=autocomplete_kwargs['autocomplete'])
                    | Q(name__contains=autocomplete_kwargs['autocomplete'])
                )
            if autocomplete_kwargs['username_autocomplete']:
                filter_args.append(
                    Q(namespace__name__contains=autocomplete_kwargs['username_autocomplete'])
                )
            if autocomplete_kwargs['tags_autocomplete']:
                if ' ' in autocomplete_kwargs['tags_autocomplete']:
                    tags = autocomplete_kwargs['tags_autocomplete']
                    tags = tags.split(' ')
                    filter_args.extend([Q(full_metadata__tags__contains=x) for x in tags])
                else:
                    filter_args.append(
                        Q(full_metadata__tags__contains=autocomplete_kwargs['tags_autocomplete'])
                    )

            return LegacyRole.objects.filter(*filter_args).order_by(order_by)

        return LegacyRole.objects.all().order_by(order_by)


class LegacyRolesViewSet(LegacyRoleBaseViewSet):
    """A list of legacy roles."""


class LegacyRoleImportsViewSet(LegacyRoleBaseViewSet):
    """Legacy role imports."""

    def _validate_create_kwargs(self, kwargs):
        try:
            assert kwargs.get('github_user') is not None
            assert kwargs.get('github_user') != ''
            assert kwargs.get('github_repo') is not None
            assert kwargs.get('github_repo') != ''
            if kwargs.get('alternate_role_name'):
                assert kwargs.get('alternate_role_name') != ''
        except Exception as e:
            return e

    def create(self, request):
        """Import a new role or new role version."""
        data = request.data

        logger.debug(f'github_user: {data.get("github_user")}')
        logger.debug(f'github_repo: {data.get("github_repo")}')
        logger.debug(f'github_reference: {data.get("github_reference")}')
        logger.debug(f'alternate_role_name: {data.get("alternate_role_name")}')

        kwargs = {
            'github_user': data.get('github_user'),
            'github_repo': data.get('github_repo'),
            'github_reference': data.get('github_reference'),
            'alternate_role_name': data.get('alternate_role_name'),
        }
        error = self._validate_create_kwargs(kwargs)
        if error:
            return HttpResponse(str(error), status=403)

        logger.debug(f'SETTINGS: {settings}')
        for x in dir(settings):
            if 'auth' in x.lower():
                logger.debug(f'SETTING {x}: {getattr(settings, x)}')
        logger.debug(f'REQUEST HEADERS: {self.request.headers}')
        logger.debug(f'REQUEST USER: {self.request.user}')
        logger.debug(
            'REQUEST USER IS AUTHENTICATED:'
            + f' {self.request.user.is_authenticated}'
        )
        logger.debug(f'REQUEST USER USERNAME: {self.request.user.username}')

        task_id = self.legacy_dispatch(legacy_role_import, kwargs=kwargs)

        role_name = kwargs['alternate_role_name'] or \
            kwargs['github_repo'].replace('ansible-role-', '')

        return Response({
            'results': [{
                'id': task_id,
                'github_user': kwargs['github_user'],
                'github_repo': kwargs['github_repo'],
                'summary_fields': {
                    'role': {
                        'name': role_name
                    }
                }
            }]
        })


class LegacyRoleViewSet(LegacyRoleBaseViewSet):
    """A single legacy role."""

    def get_object(self):
        """Helper function for access policy"""
        roleid = self.kwargs['roleid']
        return LegacyRole.objects.filter(id=roleid).first()

    @extend_schema_field(LegacyRoleSerializer)
    def retrieve(self, request, roleid=None):
        """Get a single role."""
        role = LegacyRole.objects.filter(id=roleid).first()
        serializer = LegacyRoleSerializer(role)
        return Response(serializer.data)

    def destroy(self, request, roleid=None):
        """Delete a single role."""
        role = LegacyRole.objects.filter(id=roleid).first()
        role.delete()
        return Response({'status': 'ok'})


class LegacyRoleContentViewSet(LegacyRoleBaseViewSet):
    """Documentation for a single legacy role."""

    @extend_schema_field(LegacyRoleContentSerializer)
    def retrieve(self, request, roleid=None):
        """Get content for a single role."""
        role = LegacyRole.objects.filter(id=roleid).first()
        serializer = LegacyRoleContentSerializer(role)
        return Response(serializer.data)


class LegacyRoleVersionsViewSet(LegacyRoleBaseViewSet):
    """A list of versions for a single legacy role."""

    @extend_schema_field(LegacyRoleVersionsSerializer)
    def retrieve(self, request, roleid=None):
        """Get versions for a single role."""
        role = LegacyRole.objects.filter(id=roleid).first()
        versions = role.full_metadata.get('versions', [])
        transformed = LegacyRoleVersionsSerializer(versions)
        paginated = {
            'count': len(transformed.data),
            'next': None,
            'next_link': None,
            'previous': None,
            'previous_link': None,
            'results': transformed.data[:]
        }
        return Response(paginated)
