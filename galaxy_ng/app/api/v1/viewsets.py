import datetime
import time

from django.urls import include, path
from rest_framework import routers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination

from pulpcore.plugin.viewsets import OperationPostponedResponse
from pulpcore.plugin.tasking import dispatch
from pulpcore.app.models import Task
from pulpcore.plugin.models import ContentArtifact
from pulp_ansible.app.models import CollectionVersion
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app.api.v1.tasks import legacy_role_import
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.api.v1.serializers import LegacyRoleSerializer
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


class LegacyRolesSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyRoleViewSet(viewsets.ModelViewSet):
    queryset = LegacyRole.objects.all()
    serializer = LegacyRoleSerializer
    serializer_class = LegacyRoleSerializer
    #permission_classes = [access_policy.CollectionAccessPolicy]
    permission_classes = [AllowAny]
    pagination_class = LegacyRolesSetPagination

    def create(self, validated_data):
        #print(f'CREATE: {validated_data}')
        #for x in dir(validated_data):
        #    try:
        #        print(f'\t{x} -> {getattr(validated_data, x)}')
        #    except Exception as e:
        #        pass
        print(f'github_user: {validated_data.data.get("github_user")}')
        print(f'github_repo: {validated_data.data.get("github_repo")}')
        print(f'github_reference: {validated_data.data.get("github_reference")}')
        print(f'alternate_role_name: {validated_data.data.get("alternate_role_name")}')
        #return Response({})
        kwargs = {
            'github_user': validated_data.data.get("github_user"),
            'github_repo': validated_data.data.get("github_repo"),
            'github_reference': validated_data.data.get("github_reference"),
            'alternate_role_name': validated_data.data.get("alternate_role_name"),
        }
        task = dispatch(legacy_role_import, kwargs=kwargs)
        print(f'TASK: {task}')
        #for x in dir(task):
        #    try:
        #        print(f'TASK.{x} -> {getattr(task, x)}')
        #    except:
        #        pass
        hashed = hash(str(task.pulp_id))
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
        #return OperationPostponedResponse(task, validated_data)

    def get_task(self, request):
        #print(f'GET TASK: {args}')
        #print(f'GET TASK: {kwargs}')
        print(f'GET TAKS: {request}')
        task_id = int(request.GET.get('id', None))
        print(f'GET TASK id: {task_id}')

        this_task = None
        for t in Task.objects.all():
            tid = str(t.pulp_id)
            thash = hash(tid)
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

