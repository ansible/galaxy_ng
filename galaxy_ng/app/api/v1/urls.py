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



'''
class ImportTasks:

    @staticmethod
    def legacy_role_import(github_user=None, github_repo=None, github_reference=None, alternate_role_name=None):
        print('START LEGACY ROLE IMPORT')
        #time.sleep(3)
        for x in range(0, 5):
            print(x)
            time.sleep(1)
        print('STOP LEGACY ROLE IMPORT')
        return True
'''

class LegacyRolesSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyRoleSerializer(serializers.ModelSerializer):

    id = serializers.SerializerMethodField()
    created = serializers.SerializerMethodField()
    modified = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    github_user = serializers.SerializerMethodField()
    github_repo = serializers.SerializerMethodField()
    github_branch = serializers.SerializerMethodField()
    commit = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    summary_fields = serializers.SerializerMethodField()

    class Meta:
        model = CollectionVersion
        fields = [
            'id',
            'created',
            'modified',
            'url',
            'github_user',
            'github_repo',
            'github_branch',
            'commit',
            'namespace',
            'name',
            'version',
            'tags',
            'summary_fields'
        ]
        #fields = ['__all__', 'tags']

    def get_id(self, obj):
        return obj.pulp_id

    def get_url(self, obj):
        return None

    def _get_git_url(self, obj):
        # https://github.com/pulp/pulp_ansible/blob/main/pulp_ansible/app/galaxy/v3/serializers.py#L274
        content_artifact = ContentArtifact.objects.select_related("artifact").filter(content=obj)
        if content_artifact:
            if not content_artifact.get().artifact:
                return content_artifact.get().remoteartifact_set.all()[0].url[:-47]

    def _get_git_commit(self, obj):
        # https://github.com/pulp/pulp_ansible/blob/main/pulp_ansible/app/galaxy/v3/serializers.py#L282
        content_artifact = ContentArtifact.objects.select_related("artifact").filter(content=obj)
        if content_artifact:
            if not content_artifact.get().artifact:
                return content_artifact.get().remoteartifact_set.all()[0].url[-40:]

    def get_created(self, obj):
        return obj._created

    def get_modified(self, obj):
        return obj.pulp_created

    def get_github_user(self, obj):
        return obj.namespace

    def get_github_repo(self, obj):
        url = self._get_git_url(obj)
        if url:
            url = url.replace('https://github.com/', '')
            return url.split('/')[1]

    def get_github_branch(self, obj):
        return 'branchname?'

    def get_commit(self, obj):
        return self._get_git_commit(obj)

    def get_tags(self, obj):
        return [x.name for x in obj.tags.all()]

    def get_summary_fields(self, obj):
        namespace = Namespace.objects.filter(name=obj.namespace).first()
        versions = []
        if hasattr(obj, '_versions'):
            versions = obj._versions
        return {
            'dependencies': [],
            'namespace': {
                'id': namespace.id,
                'name': obj.namespace
            },
            'provider_namespace': {
                'id': namespace.id,
                'name': obj.namespace
            },
            'repository': {
            },
            'tags': [x.name for x in obj.tags.all()],
            'versions': versions
        }


class LegacyRoleViewSet(viewsets.ModelViewSet):
    #queryset = CollectionVersion.objects.all()
    serializer = LegacyRoleSerializer
    serializer_class = LegacyRoleSerializer
    #permission_classes = [access_policy.CollectionAccessPolicy]
    permission_classes = [AllowAny]
    pagination_class = LegacyRolesSetPagination

    '''
    def dispatch(self, request, *args, **kwargs):
        #import pdb; pdb.set_trace() # or print debug statements
        print(f'dispatch request:{request} args:{args} kwargs:{kwargs}')
        super(LegacyRoleViewSet, self).dispatch(request, *args, **kwargs)
    '''

    def get_queryset(self, *args, **kwargs):
        #return CollectionVersion.objects.filter(namespace='geerlingguy')
        #return CollectionVersion.objects.filter(tags__name__in=['ng_role'])
        cvs = CollectionVersion.objects.filter(tags__name__in=['ng_role']).order_by('version')
        groups = {}
        for cv in cvs:
            key = (cv.namespace, cv.name)
            if key not in groups:
                groups[key] = []
            groups[key].append(cv)
        keys = sorted(groups.keys())
        results = []
        for key in keys:
            this_cv = groups[key][-1]
            this_cv._versions = [x.version for x in groups[key]]
            this_cv._created = groups[key][0].pulp_created
            results.append(this_cv)

        print(f'TOTAL KEYS: {len(keys)}')
        print(f'TOTAL ROLES: {len(results)}')

        return results

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
        return Response({'results': [{'id': hashed}]})
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


#def legacy_role_import(github_user=None, github_repo=None, github_reference=None, alternate_role_name=None):
#    return True



# path("tasks/", viewsets.TaskViewSet.as_view({"get": "list"}), name="tasks-list"),
urlpatterns = [
    path('imports', LegacyRoleViewSet.as_view({"post": "create", "get": "get_task"}), name='legacy_role-imports1'),
    path('imports/', LegacyRoleViewSet.as_view({"post": "create", "get": "get_task"}), name='legacy_role-imports2'),
    path('roles', LegacyRoleViewSet.as_view({"get": "list"}), name='legacy_role-list')
]
#print(f'v1: {urlpatterns}')
