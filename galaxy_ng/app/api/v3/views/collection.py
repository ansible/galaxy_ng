import copy
import datetime
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

from galaxy_importer.utils.roles import get_path_role_version
from galaxy_importer.utils.roles import get_path_role_name
from galaxy_importer.utils.roles import get_path_role_namespace
from galaxy_importer.utils.roles import path_is_role


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
    def __str__(self):
        return f'<FakeFileName: {self.namespace}>'
    def __repr__(self):
        return f'<FakeFileName: {self.namespace}>'


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
        for k,v in args[0].data.items():
            data[k] = v

        # the permission class needs to inspect the namespace to determine RBAC,
        # so we -need- to know it now ... but -how- do we get it!?!? ...
        #   namespace = models.Namespace.objects.get(name=data['filename'].namespace)

        if data.get('namespace'):
            data['filename'] = FakeFileName(data['namespace'])
        elif data.get('repository'):
            filename = data.get('repository')
            filename = filename.replace('https://github.com/', '')
            filename = filename.split('/')[0]
            data['filename'] = FakeFileName(filename)
        else:
            data['filename'] = FakeFileName('amazon')

        self._namespace = data['filename'].namespace
        self._name = data.get('name')

        print(f'PDATA: {data}')
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
        task = dispatch(
            run_import,
            args=[self._git_repository, self._git_ref],
            kwargs={'namespace': self._namespace, 'name': self._name}
        )
        #return HttpResponse(status=201)
        return OperationPostponedResponse(task, request)


def run_import(git_repo, git_ref, namespace=None, name=None):
    gi = GitImport(git_repo, git_ref, namespace=None, name=None)
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
    _is_role = False

    def __init__(self, git_repo, git_ref, namespace=None, name=None):
        self._git_repository = git_repo
        self._git_ref = git_ref
        self._namespace = namespace
        self._name = name
        self._is_role = False

    def clone_repo(self):
        self._clone_path = tempfile.mkdtemp()
        cmd = f'git clone {self._git_repository} {self._clone_path}'
        pid = subprocess.run(cmd, shell=True)

        cmd = f'cd {self._clone_path}; git log -1 -format="%H"'
        pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._head = pid.stdout.decode('utf-8').strip()

        if self._git_ref is None:
            self._git_ref = self._head

        self._is_role = path_is_role(self._clone_path)

    @property
    def galaxy_meta(self):

        fpath = os.path.join(self._clone_path, 'galaxy.yml')
        if not os.path.exists(fpath):

            # handle v1 roles ...
            mpath = os.path.join(self._clone_path, 'meta', 'main.yml')
            if os.path.exists(mpath):
                with open(mpath, 'r') as f:
                    data = yaml.load(f.read())

                # shim the role name ...
                #data['name'] = data['galaxy_info']['role_name']
                if self._name:
                    data['name'] = self._name
                else:
                    data['name'] = get_path_role_name(self._clone_path)

                # get the "namespace" via the git url ...
                #data['namespace'] = self._git_repository.replace('https://github.com/', '').split('/')[0]
                if self._namespace:
                    data['namespace'] = self._namespace
                else:
                    data['namespace'] = get_path_role_namespace(self._clone_path)

                # what is the version?
                data['version'] = get_path_role_version(self._clone_path)

                print(f'GALAXY_META: {data}')
                return data

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
        '''
        print(f'GSYNC: {gsync}')
        for x in dir(gsync):
            try:
                print(f'GSYNC.{x}: {getattr(gsync, x)}')
            except Exception as e:
                pass
        '''

        # run importer!? ... done by sync

        # create collection version from importer results!? ... done by sync

        # save collection version!? ... done by sync
        cvs = CollectionVersion.objects.all().filter(
            namespace=self._namespace,
            name=self._name,
            version=self._version,
            #repository=repository
        )

        try:
            cv = cvs[0]
        except Exception as e:

            cvs = CollectionVersion.objects.all().filter(
                namespace=self._namespace,
                name=self._name
            )
            cversions = [x.version for x in cvs]

            raise Exception(f'no CV version {self._version} found: {cversions}')

        #####################################
        # flag is_role ...
        #####################################
        if self._is_role:
            cv.is_role = True
            cv.save()

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
