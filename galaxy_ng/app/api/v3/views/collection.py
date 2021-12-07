import copy
import os
import subprocess
import time
import tempfile
import yaml

from django.http import HttpResponse

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.tasks.promotion import call_copy_task

from pulp_ansible.app.models import GitRemote
from pulp_ansible.app.models import AnsibleRepository
from pulp_ansible.app.models import CollectionVersion
from pulp_ansible.app.models import AnsibleDistribution
from pulp_ansible.app.tasks.git import synchronize as git_synchronize

import asyncio
from pulpcore.plugin.stages import DeclarativeVersion
from pulpcore.plugin.stages import ContentAssociation
from pulp_ansible.app.tasks.git import GitFirstStage
from pulpcore.plugin.stages import create_pipeline, EndStage
from pulpcore.plugin.tasking import dispatch
from pulpcore.app.models.task import Task

from pulpcore.plugin.viewsets import OperationPostponedResponse
from pulp_ansible.app.tasks.copy import copy_content


'''
 71     path(
 72         "git/sync/collection/",
 73         views.CollectionGitSyncView.as_view({"post": "create"}),
 74         name="collection-git-sync",
 75     ),
'''

'''
class CollectionVersionViewSet(api_base.LocalSettingsMixin,
                               ViewNamespaceSerializerContextMixin,
                               pulp_ansible_views.CollectionVersionViewSet):
    serializer_class = CollectionVersionSerializer
    permission_classes = [access_policy.CollectionAccessPolicy]
    list_serializer_class = CollectionVersionListSerializer
'''


class FakeFileName:
    def __init__(self, namespace):
        self.namespace = namespace


class CollectionGitSyncView(api_base.ViewSet):

    permission_classes = [access_policy.CollectionAccessPolicy]

    _git_repository = None
    _git_ref = None
    _clone_path = None
    _head = None
    _remote_name = None
    _repo_name = None
    _namespace = None
    _name = None
    _version = None

    def _get_data(self, *args, **kwargs):
        print(f'GET_DATA ARGS: {args}')
        print(f'GET_DATA KWARGS: {kwargs}')
        print(f'GET_DATA ARGS.data: {args[0].data}')

        data = copy.deepcopy(kwargs)

        # the permission class needs to inspect the namespace to determine RBAC,
        # so we -need- to know it now ... but -how- do we get it!?!? ...
        #   namespace = models.Namespace.objects.get(name=data['filename'].namespace)
        data['filename'] = FakeFileName('amazon')

        return data

    def create(self, *args, **kwargs):
        print(f'CREATE ARGS: {args}')
        print(f'CREATE KWARGS: {kwargs}')
        print(f'CREATE ARGS.data: {args[0].data}')

        request = args[0]
        data = args[0].data

        self._git_repository = data.get('repository')
        self._git_ref = data.get('git_ref')

        #task = dispatch(git_synchronize, args=[self._git_repository, self._git_ref])
        task = dispatch(run_import, args=[self._git_repository, self._git_ref])
        #return HttpResponse(status=201)
        return OperationPostponedResponse(task, request)


def run_import(git_repo, git_ref):
    gi = GitImport(git_repo, git_ref)
    gi.create()


class GitImport:

    _git_repository = None
    _git_ref = None
    _clone_path = None
    _head = None
    _remote_name = None
    _repo_name = None
    _namespace = None
    _name = None
    _version = None

    def __init__(self, git_repo, git_ref):
        self._git_repository = git_repo
        self._git_ref = git_ref

    def clone_repo(self):
        self._clone_path = tempfile.mkdtemp()
        cmd = f'git clone {self._git_repository} {self._clone_path}'
        pid = subprocess.run(cmd, shell=True)

        cmd = f'cd {self._clone_path}; git log -1 -format="%H"'
        pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._head = pid.stdout.decode('utf-8').strip()

        if self._git_ref is None:
            self._git_ref = self._head

    @property
    def galaxy_meta(self):
        fpath = os.path.join(self._clone_path, 'galaxy.yml')
        if not os.path.exists(fpath):
            return {}

        with open(fpath, 'r') as f:
            data = yaml.load(f.read())

        return data

    def create(self):

        # clone it so we can collect data ...
        self.clone_repo()

        # get the info
        gdata = self.galaxy_meta
        print(f'CREATE GALAXY.YML: {gdata}')

        # get the namespace
        self._namespace = gdata['namespace']

        # get the name
        self._name = gdata['name']

        # get the version
        self._version = gdata['version']

        # set the temporary inbound repo name
        self._repo_name = f'inbound-{self._name}'

        #####################################
        # sync machinery
        #####################################

        # create remote if not exists <namespace>.<name>/
        #   name: <namespace>.<name>/
        #   url: <git_repository>
        #   metadata_only: True
        #   git_ref: <git_ref>

        self._remote_name = f'{self._namespace}.{self._name}/'
        candidates = GitRemote.objects.all().filter(name=self._remote_name)
        if candidates:
            remote = candidates[0]
            if remote.git_ref != self._git_ref:
                remote.git_ref = self._git_ref
                remote.save()
        else:
            remote = GitRemote(
                name=self._remote_name,
                url=self._git_repository,
                git_ref=self._git_ref,
                metadata_only=True
            )
            remote.save()
        print(f'REMOTE: {remote}')

        # create if not exists inbound-<namespace> repository
        candidates = AnsibleRepository.objects.all().filter(name=self._repo_name)
        if candidates:
            repository = candidates[0]
        else:
            repository = AnsibleRepository(
                name=self._repo_name
            )
            repository.save()
        print(f'REPOSITORY: {repository}')

        # create distribution
        candidates = AnsibleDistribution.objects.all().filter(name=self._repo_name)
        if candidates:
            distro = candidates[0]
            distro.repository = repository
            distro.save()
        else:
            distro = AnsibleDistribution(
                name=self._repo_name,
                base_path=self._repo_name,
                repository=repository
            )
        print(f'DISTRO: {distro}')

        # run sync ...
        #   <Repository: inbound-aws; Version: 5>
        gsync = git_synchronize(remote.pk, repository.pk)
        print(f'GSYNC: {gsync}')
        for x in dir(gsync):
            try:
                print(f'GSYNC.{x}: {getattr(gsync, x)}')
            except Exception as e:
                pass

        # run importer!? ... done by sync

        # create collection version from importer results!? ... done by sync

        # save collection version!? ... done by sync
        cvs = CollectionVersion.objects.all().filter(
            namespace=self._namespace,
            name=self._name,
            version=self._version,
            #repository=repository
        )
        cv = cvs[0]

        #####################################
        # copy bits from inbound to staging
        #####################################
        #staging =  AnsibleDistribution.objects.get(name="staging").repository
        #async_task = call_copy_task(cv, repository, staging)

        #####################################
        # copy bits from staging to published
        #####################################
        published =  AnsibleDistribution.objects.get(name="published").repository
        async_task = call_copy_task(cv, repository, published)

        #print(f'FINAL STATE: {gsync.state}')
        return HttpResponse(status=201)
