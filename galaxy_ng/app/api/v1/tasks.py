import asyncio
import copy
import datetime
import subprocess
import time
import tempfile

from pprint import pprint

from django.conf import settings

from pulp_ansible.app.models import AnsibleDistribution
from pulp_ansible.app.models import AnsibleRepository
from pulp_ansible.app.models import Collection
from pulp_ansible.app.models import CollectionVersion
from pulp_ansible.app.models import GitRemote
from pulp_ansible.app.models import Tag
from pulp_ansible.app.tasks.git import synchronize as git_synchronize
from pulp_ansible.app.tasks.git import GitFirstStage


from pulpcore.plugin.models import Content
from pulpcore.plugin.models import ContentArtifact
from pulpcore.plugin.models import Remote
from pulpcore.plugin.models import RemoteArtifact
from pulpcore.plugin.stages import DeclarativeVersion
from pulpcore.plugin.stages import Stage
from pulpcore.plugin.stages.api import EndStage
from pulpcore.plugin.stages.api import create_pipeline
from pulpcore.plugin.stages.artifact_stages import ArtifactDownloader
from pulpcore.plugin.stages.artifact_stages import ArtifactSaver
from pulpcore.plugin.stages.artifact_stages import QueryExistingArtifacts
from pulpcore.plugin.stages.artifact_stages import RemoteArtifactSaver
from pulpcore.plugin.stages.content_stages import ContentAssociation
from pulpcore.plugin.stages.content_stages import ContentSaver
from pulpcore.plugin.stages.content_stages import QueryExistingContents
from pulpcore.plugin.stages.content_stages import ResolveContentFutures
from pulpcore.plugin.tasking import add_and_remove

#from galaxy_ng.app.models import Namespace
#from galaxy_ng.app.tasks.promotion import move_content
import galaxy_ng.app.utils.roles as roles

from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole


def get_role_version(
    checkout_path = None,
    github_user=None,
    github_repo=None,
    github_reference=None,
    alternate_role_name=None,
):

    if checkout_path is None:
        clone_url = f'https://github.com/{github_user}/{github_repo}'
        checkout_path = tempfile.mkdtemp()
        cmd = f'git clone {clone_url} {checkout_path}'
        print(cmd)
        pid = subprocess.run(cmd, shell=True)

    pid = subprocess.run('git fetch --tags', shell=True, cwd=checkout_path, stdout=subprocess.PIPE)
    pid = subprocess.run('git tag -l', shell=True, cwd=checkout_path, stdout=subprocess.PIPE)
    tags = pid.stdout.decode('utf-8')
    tags = tags.split('\n')
    tags = [x.strip() for x in tags if x.strip()]

    if github_reference and github_reference in tags:
        return github_reference

    if tags:
        return tags[-1]

    version = roles.get_path_role_version(checkout_path)
    return version


def get_tag_commit_hash(git_url, tag, checkout_path=None):
    if checkout_path is None:
        checkout_path = tempfile.mkdtemp()
        pid = subprocess.run(f'git clone {git_url} {checkout_path}', shell=True)
    pid = subprocess.run("git log -1 --format='%H'", shell=True, cwd=checkout_path, stdout=subprocess.PIPE)
    commit_hash = pid.stdout.decode('utf-8').strip()
    return commit_hash


def legacy_role_import(github_user=None, github_repo=None, github_reference=None, alternate_role_name=None):
    print('START LEGACY ROLE IMPORT')

    role_name = alternate_role_name or github_repo.replace('ansible-role-', '')
    if LegacyNamespace.objects.filter(name=github_user).count() == 0:
        print('CREATE NEW NAMESPACE {github_user}')
        namespace,_ = LegacyNamespace.objects.get_or_create(name=github_user)
    else:
        print('USE EXISTING NAMESPACE {github_user}')
        namespace = LegacyNamespace.objects.filter(name=github_user).first()

    with tempfile.TemporaryDirectory() as checkout_path:

        clone_url = f'https://github.com/{github_user}/{github_repo}'
        cmd = f'git clone {clone_url} {checkout_path}'
        print(cmd)
        pid = subprocess.run(cmd, shell=True)
        if github_reference is not None:
            cmd = f'git -c advice.detachedHead=false checkout tags/{github_reference}'
            pid = subprocess.run(cmd, shell=True, cwd=checkout_path)
        else:
            github_reference = get_role_version(
                checkout_path=checkout_path,
                github_user=github_user,
                github_repo=github_repo,
                github_reference=github_reference,
                alternate_role_name=alternate_role_name,
                namespace=namespace.name,
                collection_name=collection_name
            )
        print(f'GITHUB_REFERENCE: {github_reference}')

        # check if this namespace/name/version has already been imported
        old = LegacyRole.objects.filter(namespace=namespace, name=role_name).first()
        if old is not None:
            old_versions = old.full_metadata.get('versions', [])
            old_versions = [x['name'] for x in old_versions]
            if github_reference in old_versions:
                raise Exception(f'{namespace.name}.{role_name} {github_reference} has already been imported')

        github_commit = get_tag_commit_hash(clone_url, github_reference, checkout_path=checkout_path)
        print(f'GITHUB_COMMIT: {github_reference}')

        role_meta = roles.get_path_role_meta(checkout_path)
        role_tags = role_meta.get('galaxy_info', {}).get('galaxy_tags', [])
        if role_tags is None:
            role_tags = []
        print(f'TAGS: {role_tags}')

        galaxy_info = role_meta.get('galaxy_info', {})
        new_full_metadata = {
            'imported': datetime.datetime.now().isoformat(),
            'clone_url': clone_url,
            'tags': role_tags,
            'commit': github_commit,
            'github_repo': github_repo,
            'github_reference': github_reference,
            'issue_tracker_url': clone_url + '/issues',
            'dependencies': [],
            'versions': [],
            'description': galaxy_info.get('description', ''),
            'license': galaxy_info.get('galaxy_info', {}).get('license', ''),
        }

        # Make the object
        this_role,_ = LegacyRole.objects.get_or_create(
            namespace=namespace,
            name=role_name
        )

        # Combine old versions with new ...
        old_metadata = copy.deepcopy(this_role.full_metadata)

        new_full_metadata['versions'] = old_metadata.get('versions', [])
        new_full_metadata['versions'].append({
            'name': github_reference,
            'release_date': datetime.datetime.now().isoformat()
        })

        # Save the new metadata
        this_role.full_metadata = new_full_metadata
        this_role.save()

    print('STOP LEGACY ROLE IMPORT')
    return True

