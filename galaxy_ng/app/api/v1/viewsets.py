import datetime
import logging

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication
)
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError

from pulpcore.plugin.models import Task
from pulpcore.plugin.tasking import dispatch

from galaxy_ng.app.api.v1.tasks import (
    legacy_role_import,
    legacy_sync_from_upstream
)
from galaxy_ng.app.api.v1.models import (
    LegacyNamespace,
    LegacyRole
)
from galaxy_ng.app.api.v1.serializers import (
    LegacyRoleSerializer,
    LegacyRoleContentSerializer,
    LegacyRoleVersionsSerializer,
    LegacyUserSerializer
)


logger = logging.getLogger(__name__)


class LegacyUserSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyUsersViewSet(viewsets.ModelViewSet):
    """
    A list of legacy users.

    The community UI has a view to list all legacy users.
    Each user is clickable and brings the browser to a
    page with a list of roles created by the user.

    Rather than make a hacky unmaintable viewset that
    aggregates usernames from the roles, this viewset
    goes directly to the legacy namespace/user table.

    We do not want to create this view from v3 namespaces
    because many/most legacy namespaces do not conform
    to the v3 namespace character requirements.

    TODO: allow edits of the avatar url
    TODO: allow edits of the "owners"
    TODO: allow mapping to a real namespace
    """

    queryset = LegacyNamespace.objects.all().order_by('name')
    serializer = LegacyUserSerializer
    serializer_class = LegacyUserSerializer
    permission_classes = [AllowAny]
    pagination_class = LegacyUserSetPagination

    def get_queryset(self):

        logger.debug(f'QUERY_PARAMS: {self.request.query_params}')

        keywords = None
        if self.request.query_params.get('keywords'):
            keywords = self.request.query_params.get('keywords').rstrip('/')

        order_by = 'name'
        if self.request.query_params.get('order_by'):
            order_by = self.request.query_params.get('order_by').rstrip('/')

        if self.request.query_params.get('name'):
            name = self.request.query_params.get('name').rstrip('/')
            return LegacyNamespace.objects.filter(name=name).order_by(order_by)

        if keywords:
            return LegacyNamespace.objects.filter(
                Q(name__contains=keywords)
            ).order_by(order_by)

        return LegacyNamespace.objects.all().order_by(order_by)

    def retrieve(self, request, pk=None):
        """Get a single user."""
        user = LegacyNamespace.objects.filter(id=pk).first()
        serializer = LegacyUserSerializer(user)
        return Response(serializer.data)


class LegacyRolesSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyTasksViewset:
    """
    Legacy task helper.

    v1 task ids were integer values and have a different
    schema and states from the pulp tasking system.

    This set of functions will reshape a pulp task into
    something compatible with v1 clients such as the
    galaxy cli.
    """

    def legacy_task_hash(self, pulp_id):
        """Transform a uuid into an integer."""
        return abs(hash(str(pulp_id)))

    def legacy_dispatch(self, function, kwargs=None):
        """Dispatch wrapper for legacy tasks."""
        task = dispatch(function, kwargs=kwargs)
        hashed = self.legacy_task_hash(task.pulp_id)
        return hashed

    @action(detail=True, methods=['get'], name="Get task")
    def get_task(self, request, id=None):
        """Get a pulp task via the transformed v1 integer task id."""
        logger.debug(f'GET TASK: {request}')
        if id:
            task_id = id
        else:
            task_id = int(request.GET.get('id', None))
        logger.debug(f'GET TASK id: {task_id}')

        # iterate through most recent tasks to find the matching uuid
        this_task = None
        for t in Task.objects.all().order_by('started_at').reverse():
            tid = str(t.pulp_id)
            thash = self.legacy_task_hash(tid)
            if thash == task_id:
                this_task = t
                break

        logger.debug(f'FOUND TASK: {this_task} ..')

        # figure out the v1 compatible state
        state_map = {
            'COMPLETED': 'SUCCESS'
        }
        state = this_task.state.upper()
        state = state_map.get(state, state)

        # figure out the message type
        type_map = {
            'RUNNING': 'INFO',
            'WAITING': 'INFO',
            'COMPLETED': 'SUCCESS'
        }
        mtype = type_map.get(state, state)

        # generate a message for the response
        msg = ''
        if state == 'SUCCESS':
            msg = 'role imported successfully'
        elif state == 'RUNNING':
            msg = 'running'
        if this_task.error:
            if this_task.error.get('traceback'):
                msg = (
                    this_task.error['description']
                    + '\n'
                    + this_task.error['traceback']
                )

        logger.debug(f'STATE:{state} MTYPE:{mtype}')
        return Response({'results': [
            {
                'state': state,
                'id': task_id,
                'summary_fields': {
                    'task_messages': [{
                        'id': datetime.datetime.now().isoformat(),
                        'message_text': msg,
                        'message_type': mtype,
                        'state': state
                    }]
                }
            }
        ]})


class LegacyRoleBaseViewSet(viewsets.ModelViewSet, LegacyTasksViewset):
    """Base class for legacy roles."""

    queryset = LegacyRole.objects.all().order_by('full_metadata__created')
    serializer = LegacyRoleSerializer
    serializer_class = LegacyRoleSerializer
    permission_classes = [AllowAny]
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

        # validate is admin or gitub_user == auth_user ...
        if not self.request.user.is_authenticated:
            return HttpResponse('authentication required', status=403)
        if not self.request.user.is_superuser and not \
                self.request.user.username == kwargs['github_user']:
            return HttpResponse('invalid permissions', status=403)

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

    def retrieve(self, request, roleid=None):
        """Get a single role."""
        role = LegacyRole.objects.filter(id=roleid).first()
        serializer = LegacyRoleSerializer(role)
        return Response(serializer.data)

    def destroy(self, request, roleid=None):
        """Delete a single role."""
        role = LegacyRole.objects.filter(id=roleid).first()

        # ensure the github_user matches the request user
        username = request.user.get_username()
        if username != role.namespace.name and not request.user.is_superuser:
            raise ValidationError({
                'default': 'you do not have permission to modify this resource'
            })

        role.delete()
        return Response({'status': 'ok'})


class LegacyRoleContentViewSet(LegacyRoleBaseViewSet):
    """Documentation for a single legacy role."""

    def retrieve(self, request, roleid=None):
        """Get content for a single role."""
        role = LegacyRole.objects.filter(id=roleid).first()
        serializer = LegacyRoleContentSerializer(role)
        return Response(serializer.data)


class LegacyRoleVersionsViewSet(LegacyRoleBaseViewSet):
    """A list of versions for a single legacy role."""

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


class LegacyRolesSyncViewSet(viewsets.ViewSet, LegacyTasksViewset):
    """Load roles from an upstream v1 source."""

    def create(self, request):
        """Create a new sync task."""
        kwargs = {
            'baseurl': request.data.get(
                'baseurl',
                'https://galaxy.ansible.com/api/v1/roles/'
            ),
            'github_user': request.data.get('github_user'),
            'role_name': request.data.get('role_name'),
            'role_version': request.data.get('role_name'),
            'limit': request.data.get('limit')
        }
        logger.debug(f'REQUEST DATA: {request.data}')
        logger.debug(f'REQUEST kwargs: {kwargs}')

        # only superuser should be able to sync roles
        logger.debug(f'REQUEST.USER: {self.request.user}')
        if not self.request.user.is_superuser:
            raise ValidationError({
                'default': 'you do not have permission to modify this resource'
            }, status=403)

        task_id = self.legacy_dispatch(legacy_sync_from_upstream, kwargs=kwargs)
        return Response({'task': task_id})
