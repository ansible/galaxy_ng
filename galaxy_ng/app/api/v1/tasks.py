import asyncio
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

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.tasks.promotion import move_content
import galaxy_ng.app.utils.roles as roles

from unittest.mock import Mock
from unittest.mock import patch


GOLDEN_NAME = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH
STAGING_NAME = settings.GALAXY_API_STAGING_DISTRIBUTION_BASE_PATH
REQUIRE_APPROVAL = settings.GALAXY_REQUIRE_CONTENT_APPROVAL


def get_or_create_tag(tagname):
    thistag = Tag.objects.filter(name=tagname).first()
    if thistag is None:
        thistag = Tag(name=tagname)
        thistag.save()
    return thistag


def get_or_create_namespace(name):
    ns = Namespace.objects.filter(name=name).first()
    if ns is None:
        ns = Namespace(name=name)
        ns.save()
    return ns


def get_or_create_collection(namespace, name):
    col = Collection.objects.filter(namespace=str(namespace), name=name).first()
    if col is None:
        col = Collection(namespace=str(namespace), name=name)
        col.save()
    return col


def get_or_create_remote(name, git_url, git_ref):
    gr = GitRemote.objects.filter(name=name, url=git_url, git_ref=git_ref).first()
    if gr is None:
        gr = GitRemote(
			name=name,
			url=git_url,
			git_ref=git_ref,
			metadata_only=True
		)
        gr.save()
    return gr


def get_or_create_repository(name):
    repo = AnsibleRepository.objects.filter(name=name).first()
    if repo is None:
        repo = AnsibleRepository(name=name)
        repo.save()
    return repo


def get_or_create_distribution(name, repository):
    repo = AnsibleDistribution.objects.filter(name=name).first()
    if repo is None:
        repo = AnsibleDistribution(
            name=name,
            base_path=name,
            repository=repository
        )
        repo.save()
    return repo


def get_role_version(
    checkout_path = None,
    github_user=None,
    github_repo=None,
    github_reference=None,
    alternate_role_name=None,
    namespace=None,
    collection_name=None
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

    #print(f'TAGS: {tags}')
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


def get_or_create_collection_version(
    checkout_path=None,
    namespace=None,
    collection=None,
    collection_name=None,
    collection_version=None,
    description=None,
    github_user=None,
    github_repo=None,
    github_reference=None,
    alternate_role_name=None,
    git_url=None,
    git_commit_sha=None,
    tags=None
):

    git_url = f'https://github.com/{github_user}/{github_repo}'
    git_ref = get_tag_commit_hash(git_url, collection_version, checkout_path=checkout_path)
    print(f'GIT_REF: {git_ref}')
    remote_name = f'{namespace.name}.{collection_name}/'
    remote = get_or_create_remote(remote_name, git_url, git_ref)
    print(f'REMOTE: {remote}')

    repo_name = f'inbound-{namespace.name}'
    repository = get_or_create_repository(repo_name)
    distribution = get_or_create_distribution(repo_name, repository)

    print(f'REPOSITORY: {repository}')
    print(f'DISTRO: {distribution}')

    ############################################
    # bypassed results for galaxy-importer
    ############################################
    importer_results = {
        'metadata': {
            'authors': [],
            'dependencies': [],
            'description': description,
            'documentation': git_url,
            'homepage': git_url,
            'issues': git_url + '/issues',
            'license': [],
            'license_file': 'COPYING',
            'name': collection_name,
            'namespace': namespace.name,
            'readme': 'README.md',
            'repository': git_url,
            'tags': tags,
            'version': collection_version
        },
        'docs_blob': '',
        'contents': [],
        'custom_license': None,
        'requires_ansible': None
    }
    pprint(importer_results)

    ##############################################################################
    # https://github.com/pulp/pulp_ansible/blob/main/pulp_ansible/app/tasks/git.py
    ##############################################################################
    first_stage = GitFirstStage(remote)
    print(f'FIRST_STAGE1:{first_stage}')

    # skip the galaxy importer call during git_sync and return the precompiled blob
    with patch('pulp_ansible.app.tasks.collections.sync_collection') as MockSyncCollection:

        MockSyncCollection.return_value = (importer_results, None)

        print('GIT SYNCHRONIZE START')
        #git_synchronize(remote.pulp_id, repository.pulp_id, mirror=False)

        pipeline_stages = [
            first_stage,
            QueryExistingArtifacts(),
            ArtifactDownloader(),
            ArtifactSaver(),
            QueryExistingContents(),
            ContentSaver(),
            RemoteArtifactSaver(),
            ResolveContentFutures(),
        ]

        with tempfile.TemporaryDirectory(dir="."):
            with repository.new_version() as new_version:
                loop = asyncio.get_event_loop()
                stages = pipeline_stages
                stages.append(ContentAssociation(new_version, False))
                stages.append(EndStage())
                pipeline = create_pipeline(stages)
                loop.run_until_complete(pipeline)

        print(f'NEW_VERSION:{new_version}')
        print('GIT SYNCHRONIZE DONE')


    # Find the newly created collectionversion ...
    cv = CollectionVersion.objects.filter(
        namespace=namespace,
        name=collection_name,
        version=collection_version
    ).first()
    print(f'NEW CV: {cv}')

    # The CV is now in the inbound-<namespace> repo
    # promote the cv to staging or published ...
    print('PROMOTION START')
    if REQUIRE_APPROVAL:
        print(f'PROMOTION DEST == {STAGING_NAME}')
        dest_repo = AnsibleDistribution.objects.get(name=STAGING_NAME).repository
    else:
        print(f'PROMOTION DEST == {GOLDEN_NAME}')
        dest_repo = AnsibleDistribution.objects.get(name=GOLDEN_NAME).repository
    move_content(cv.pulp_id, repository.pulp_id, dest_repo.pulp_id)
    print('PROMOTION DONE')


def legacy_role_import(github_user=None, github_repo=None, github_reference=None, alternate_role_name=None):
    print('START LEGACY ROLE IMPORT')

    collection_name = alternate_role_name or github_repo.replace('ansible-role-', '')
    namespace = get_or_create_namespace(github_user)
    collection = get_or_create_collection(namespace.name, collection_name)

    with tempfile.TemporaryDirectory() as checkout_path:

        clone_url = f'https://github.com/{github_user}/{github_repo}'
        cmd = f'git clone {clone_url} {checkout_path}'
        print(cmd)
        pid = subprocess.run(cmd, shell=True)

        role_meta = roles.get_path_role_meta(checkout_path)

        github_refernce = get_role_version(
            checkout_path=checkout_path,
            github_user=github_user,
            github_repo=github_repo,
            github_reference=github_reference,
            alternate_role_name=alternate_role_name,
            namespace=namespace.name,
            collection_name=collection_name
        )

        role_meta = roles.get_path_role_meta(checkout_path)
        role_tags = role_meta.get('galaxy_info', {}).get('galaxy_tags', [])
        if role_tags is None:
            role_tags = []
        if 'ng_role' not in role_tags:
            role_tags.insert(0, 'ng_role')
        print(f'TAGS: {role_tags}')

        collection_version = get_or_create_collection_version(
            checkout_path=checkout_path,
            github_user=github_user,
            github_repo=github_repo,
            github_reference=github_reference,
            alternate_role_name=alternate_role_name,
            namespace=namespace,
            collection=collection,
            collection_name=collection_name,
            collection_version=github_reference,
            tags=role_tags
        )

    print(f'namespace:{namespace} collection:{collection} version:{github_reference} cv:{collection_version}')

    #for x in range(0, 5):
    #    print(x)
    #    time.sleep(1)

    print('STOP LEGACY ROLE IMPORT')
    return True

