import datetime
import time

from django.conf import settings
from django.http import HttpResponse
from django.urls import include, path
from rest_framework import routers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, viewsets


from rest_framework.authentication import BasicAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from pulpcore.plugin.viewsets import OperationPostponedResponse
from pulpcore.plugin.tasking import dispatch
from pulpcore.app.models import Task
from pulpcore.plugin.models import ContentArtifact
from pulp_ansible.app.models import CollectionVersion
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app.api.v1.tasks import legacy_role_import
from galaxy_ng.app.api.v1.tasks import legacy_sync_from_upstream
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.api.v1.serializers import LegacyRoleSerializer
from galaxy_ng.app.api.v1.serializers import LegacyRoleContentSerializer
from galaxy_ng.app.api.v1.serializers import LegacyRoleVersionsSerializer
from galaxy_ng.app.api.v1.serializers import LegacyUserSerializer


class LegacyUserSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyUserViewSet(viewsets.ModelViewSet):
    queryset = LegacyNamespace.objects.all()
    serializer = LegacyUserSerializer
    serializer_class = LegacyUserSerializer
    permission_classes = [AllowAny]
    pagination_class = LegacyUserSetPagination

    def get_user(self, *args, **kwargs):
        userid = kwargs.get('userid')
        user = LegacyNamespace.objects.filter(id=userid).first()
        serializer = LegacyUserSerializer(user)
        return Response(serializer.data)


class LegacyRolesSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyRoleViewSet(viewsets.ModelViewSet):
    queryset = LegacyRole.objects.all().order_by('full_metadata__created')
    serializer = LegacyRoleSerializer
    serializer_class = LegacyRoleSerializer
    #permission_classes = [access_policy.CollectionAccessPolicy]
    permission_classes = [AllowAny]
    #permission_classes = [IsAuthenticated]
    pagination_class = LegacyRolesSetPagination
    authentication_classes = [BasicAuthentication, SessionAuthentication, TokenAuthentication]

    def get_queryset(self):

        print(f'QUERY_PARAMS: {self.request.query_params}')
        github_user = None
        for keyword in ['owner__username', 'github_user', 'namespace']:
            if self.request.query_params.get(keyword):
                github_user = self.request.query_params[keyword]
                break

        name = self.request.query_params.get('name')
        if github_user and name:
            print('FILTER BY USER AND NAME')
            namespace = LegacyNamespace.objects.filter(name=github_user).first()
            return LegacyRole.objects.filter(namespace=namespace, name=name)

        elif github_user:
            print('FILTER BY USER')
            namespace = LegacyNamespace.objects.filter(name=github_user).first()
            return LegacyRole.objects.filter(namespace=namespace)

        return LegacyRole.objects.all()

    def get_role(self, *args, **kwargs):
        roleid = int(kwargs.get('roleid'))
        role = LegacyRole.objects.filter(id=roleid).first()
        serializer = LegacyRoleSerializer(role)
        return Response(serializer.data)

    def get_content(self, *args, **kwargs):
        roleid = int(kwargs.get('roleid'))
        role = LegacyRole.objects.filter(id=roleid).first()
        serializer = LegacyRoleContentSerializer(role)
        return Response(serializer.data)

    def get_versions(self, *args, **kwargs):
        roleid = int(kwargs.get('roleid'))
        role = LegacyRole.objects.filter(id=roleid).first()
        #serializer = LegacyRoleVersionsSerializer(role)
        versions = role.full_metadata.get('versions', [])
        #return Response(versions)
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

    def validate_create_kwargs(self, kwargs):
        try:
            assert kwargs.get('github_user') is not None
            assert kwargs.get('github_user') != ''
            assert kwargs.get('github_repo') is not None
            assert kwargs.get('github_repo') != ''
            if kwargs.get('alternate_role_name'):
                assert kwargs.get('alternate_role_name') != ''
        except Exception as e:
            return e

    def create(self, validated_data):

        print(f'github_user: {validated_data.data.get("github_user")}')
        print(f'github_repo: {validated_data.data.get("github_repo")}')
        print(f'github_reference: {validated_data.data.get("github_reference")}')
        print(f'alternate_role_name: {validated_data.data.get("alternate_role_name")}')

        kwargs = {
            'github_user': validated_data.data.get("github_user"),
            'github_repo': validated_data.data.get("github_repo"),
            'github_reference': validated_data.data.get("github_reference"),
            'alternate_role_name': validated_data.data.get("alternate_role_name"),
        }
        error = self.validate_create_kwargs(kwargs)
        if error:
            return HttpResponse(str(error), status=403)

        print(f'SETTINGS: {settings}')
        for x in dir(settings):
            if 'auth' in x.lower():
                print(f'SETTING {x}: {getattr(settings, x)}')
        print(f'REQUEST HEADERS: {self.request.headers}')
        print(f'REQUEST USER: {self.request.user}')
        print(f'REQUEST USER IS AUTHENTICATED: {self.request.user.is_authenticated}')
        print(f'REQUEST USER USERNAME: {self.request.user.username}')

        # validate is admin or gitub_user == auth_user ...
        if not self.request.user.is_authenticated:
            return HttpResponse('authentication required', status=403)
        if not self.request.user.is_superuser and not self.request.user.username == kwargs['github_user']:
            return HttpResponse('invalid permissions', status=403)

        task = dispatch(legacy_role_import, kwargs=kwargs)
        print(f'TASK: {task}')

        hashed = abs(hash(str(task.pulp_id)))
        print(f'NEW_TASK_ID: {task.pulp_id}')
        print(f'NEW_HASHED_TASK_ID: {hashed}')

        role_name = kwargs['alternate_role_name'] or kwargs['github_repo'].replace('ansible-role-', '')

        return Response({
            'results': [{
                'id': hashed,
                'github_user': kwargs['github_user'],
                'github_repo': kwargs['github_repo'],
                'summary_fields': {
                    'role': {
                        'name': role_name
                    }
                }
            }]
        })

    def get_task(self, request):
        #print(f'GET TASK: {args}')
        #print(f'GET TASK: {kwargs}')
        print(f'GET TASK: {request}')
        task_id = int(request.GET.get('id', None))
        print(f'GET TASK id: {task_id}')

        this_task = None
        for t in Task.objects.all():
            tid = str(t.pulp_id)
            thash = abs(hash(tid))
            #print(f'tid:{tid} thash:{thash}')
            if thash == task_id:
                this_task = t
                break

        print(f'FOUND TASK: {this_task} ..')
        '''
        for x in dir(this_task):
            try:
                print(f'task {x}: {getattr(this_task, x)}')
            except:
                pass
        '''

        state = this_task.state.upper()
        msg = ''
        if this_task.error:
            if this_task.error.get('traceback'):
                tb = this_task.error['description']
                tb += '\n'
                tb += this_task.error['traceback']
                msg += tb

        type_map = {
            'RUNNING': 'INFO',
            'WAITING': 'INFO',
            'COMPLETED': 'SUCCESS'
        }
        mtype = type_map.get(state, state)
        print(f'STATE:{state} MTYPE:{mtype}')

        state_map = {
            'COMPLETED': 'SUCCESS'
        }
        state = state_map.get(state, state)
        if state == 'SUCCESS':
            msg = 'role imported successfully'
        elif state == 'RUNNING':
            msg = 'running'

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

    def run_sync(self, request):
        kwargs = {
            'baseurl': request.data.get(
                'baseurl',
                'https://galaxy.ansible.com/api/v1/roles/'
            ),
            'github_user': request.data.get('github_user'),
            'role_name': request.data.get('role_name'),
            'role_version': request.data.get('role_name'),
        }
        task = dispatch(legacy_sync_from_upstream, kwargs=kwargs)
        hashed = abs(hash(str(task.pulp_id)))
        return Response({'task': hashed})
