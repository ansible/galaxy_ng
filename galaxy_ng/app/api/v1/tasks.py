import asyncio
import copy
import datetime
import os
import subprocess
import time
import tempfile

import requests
from urllib.parse import urlparse

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

from galaxy_importer.loaders.content import RoleLoader
from galaxy_importer.utils import markup as markup_utils

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

    print('TAG FETCH')
    pid = subprocess.run('git fetch --tags', shell=True, cwd=checkout_path, stdout=subprocess.PIPE)
    assert pid.returncode == 0, 'fetching tags failed'
    print('TAG LIST')
    pid = subprocess.run('git tag -l', shell=True, cwd=checkout_path, stdout=subprocess.PIPE)
    assert pid.returncode == 0, 'listing tags failed'

    tags = pid.stdout.decode('utf-8')
    tags = tags.split('\n')
    tags = [x.strip() for x in tags if x.strip()]
    print(f'TAGS: {tags}')

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


def get_tag_commit_date(git_url, tag, checkout_path=None):
    if checkout_path is None:
        checkout_path = tempfile.mkdtemp()
        pid = subprocess.run(f'git clone {git_url} {checkout_path}', shell=True)
    pid = subprocess.run("git log -1 --format='%ci'", shell=True, cwd=checkout_path, stdout=subprocess.PIPE)
    commit_date = pid.stdout.decode('utf-8').strip()

    # 2022-06-07 22:18:41 +0000 --> 2022-06-07T22:18:41
    parts = commit_date.split()
    print(f'COMMIT DATE PARTS: {parts}')
    ts = f"{parts[0]}T{parts[1]}"

    return ts


def legacy_role_import(github_user=None, github_repo=None, github_reference=None, alternate_role_name=None):
    print('START LEGACY ROLE IMPORT')

    # prevent empty strings?
    if not github_reference:
        github_reference = None

    role_name = alternate_role_name or github_repo.replace('ansible-role-', '')
    if LegacyNamespace.objects.filter(name=github_user).count() == 0:
        print(f'CREATE NEW NAMESPACE {github_user}')
        namespace,_ = LegacyNamespace.objects.get_or_create(name=github_user)
    else:
        print(f'USE EXISTING NAMESPACE {github_user}')
        namespace = LegacyNamespace.objects.filter(name=github_user).first()

    with tempfile.TemporaryDirectory() as checkout_path:

        clone_url = f'https://github.com/{github_user}/{github_repo}'
        cmd = f'git clone {clone_url} {checkout_path}'
        print(cmd)
        pid = subprocess.run(cmd, shell=True)
        if github_reference is not None:
            cmd = f'git -c advice.detachedHead=false checkout tags/{github_reference}'
            print(cmd.upper())
            pid = subprocess.run(cmd, shell=True, cwd=checkout_path)
        else:
            github_reference = get_role_version(
                checkout_path=checkout_path,
                github_user=github_user,
                github_repo=github_repo,
                github_reference=github_reference,
                alternate_role_name=alternate_role_name,
            )
        print(f'GITHUB_REFERENCE: {github_reference}')

        # check if this namespace/name/version has already been imported
        old = LegacyRole.objects.filter(namespace=namespace, name=role_name).first()
        if old is not None:
            old_versions = old.full_metadata.get('versions', [])
            old_versions = [x['name'] for x in old_versions]
            print(f'OLD VERSIONS: {old_versions}')
            if github_reference in old_versions:
                raise Exception(f'{namespace.name}.{role_name} {github_reference} has already been imported')

        github_commit = get_tag_commit_hash(clone_url, github_reference, checkout_path=checkout_path)
        github_commit_date = get_tag_commit_date(clone_url, github_reference, checkout_path=checkout_path)
        print(f'GITHUB_COMMIT: {github_commit}')

        role_meta = roles.get_path_role_meta(checkout_path)
        role_tags = role_meta.get('galaxy_info', {}).get('galaxy_tags', [])
        if role_tags is None:
            role_tags = []
        print(f'TAGS: {role_tags}')

        # use the importer to grok the readme
        ldr = RoleLoader(
            content_type='role',
            root=os.path.dirname(checkout_path),
            rel_path=os.path.basename(checkout_path)
        )
        readme = ldr._get_readme()
        readme_html = markup_utils._render_from_markdown(readme)

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
            'readme': readme,
            'readme_html': readme_html
        }

        # Make the object
        this_role,_ = LegacyRole.objects.get_or_create(
            namespace=namespace,
            name=role_name
        )

        # Combine old versions with new ...
        old_metadata = copy.deepcopy(this_role.full_metadata)

        new_full_metadata['versions'] = old_metadata.get('versions', [])
        ts = datetime.datetime.now().isoformat()
        new_full_metadata['versions'].append({
            'name': github_reference,
            'version': github_reference,
            'release_date': ts,
            'created': ts,
            'modified': ts,
            'active': None,
            'download_url': None,
            'url': None,
            'commit_date': github_commit_date,
            'commit_sha': github_commit
        })

        # Save the new metadata
        this_role.full_metadata = new_full_metadata
        this_role.save()

    print('STOP LEGACY ROLE IMPORT')
    return True


def legacy_sync_from_upstream(baseurl=None, github_user=None, role_name=None, role_version=None):
    print('STARTING LEGACY SYNC!')

    print('SYNC INDEX EXISTING NAMESPACES')
    nsmap = {}
    for ns in LegacyNamespace.objects.all():
        nsmap[ns.name] = ns

    print('SYNC INDEX EXISTING ROLES')
    rmap = {}
    #for role in LegacyRole.objects.all():
    #    key = (role.namespace.name, role.name)
    #    rmap[key] = role
    LegacyRole.objects.all().delete()

    parsed = urlparse(baseurl)
    _baseurl = parsed.scheme + '://' + parsed.netloc

    pagenum = 0
    next_url = baseurl
    while next_url:
        print(f'{pagenum} {next_url}')

        rr = requests.get(next_url)

        try:
            ds = rr.json()
            print(f"NEXT: {ds.get('next_link')}")
        except Exception as e:
            next_url = next_url.replace(f'page={pagenum}', f'page={pagenum+1}')
            pagenum += 1
            continue

        if not ds.get('next_link'):
            break

        for rdata in ds['results']:
            #print(f'{rdata}')
            ruser = rdata.get('github_user')
            rname = rdata.get('name')
            rkey = (ruser, rname)

            if ruser not in nsmap:
                print(f'SYNC NAMESPACE GET_OR_CREATE {ruser}')
                namespace,_ = LegacyNamespace.objects.get_or_create(name=ruser)
                nsmap[ruser] = namespace
            else:
                namespace = nsmap[ruser]

            remote_id = rdata['id']
            role_upstream_url = _baseurl + f'/api/v1/roles/{remote_id}/'
            rrr = requests.get(role_upstream_url)
            if rrr.status_code == 404:
                continue
            try:
                rds = rrr.json()
                if rds.get('detail', '').lower().strip() == 'not found':
                    continue
            except Exception as e:
                continue

            if rkey not in rmap:
                this_role,_ = LegacyRole.objects.get_or_create(
                    namespace=namespace,
                    name=rname
                )
                rmap[rkey] = this_role
            else:
                this_role = rmap[rkey]

            github_repo = rdata['github_repo']
            github_branch = rdata['github_branch']
            clone_url = f'https://github.com/{ruser}/{github_repo}'
            sfields = rdata.get('summary_fields', {})
            role_tags = sfields.get('tags', [])
            commit_hash = rdata.get('commit')
            commit_msg = rdata.get('commit_message')
            commit_url = rdata.get('commit_url')
            issue_tracker = rdata.get('issue_tracker_url', clone_url + '/issues')
            #role_versions = sfields.get('versions', [])
            role_description = rdata.get('description')
            role_license = rdata.get('license')
            role_readme = rdata.get('readme')
            role_html = rdata.get('readme_html')
            role_dependencies = sfields.get('dependencies', [])
            role_min_ansible = rdata.get('min_ansible_version')
            role_company = rdata.get('company')
            role_imported = rdata.get('imported', datetime.datetime.now().isoformat())
            role_created = rdata.get('created', datetime.datetime.now().isoformat())
            role_modified = rdata.get('modified', datetime.datetime.now().isoformat())
            role_type = rdata.get('role_type', 'ANS')

            role_versions = []
            versions_next_url = _baseurl + f'/api/v1/roles/{remote_id}/versions/'
            while versions_next_url:
                print(f'GET: {versions_next_url}')
                rrv = requests.get(versions_next_url)
                try:
                    vds = rrv.json()
                except Exception as e:
                    print(rrv.text)
                    raise Exception('invalid json')
                for _res in vds['results']:
                    role_versions.append(_res)
                if not vds.get('next_link'):
                    break
                try:
                    versions_next_url = _baseurl + vds.get('next_link')
                except TypeError as e:
                    break

            new_full_metadata = {
                'upstream_id': remote_id,
                'role_type': role_type,
                'imported': role_imported,
                'created': role_created,
                'modified': role_modified,
                'clone_url': clone_url,
                'tags': role_tags,
                'commit': commit_hash,
                'commit_message': commit_msg,
                'commit_url': commit_url,
                'github_repo': github_repo,
                'github_branch': github_branch,
                #'github_reference': github_reference,
                'issue_tracker_url': issue_tracker,
                'dependencies': role_dependencies,
                'versions': role_versions,
                'description': role_description,
                'license': role_license,
                'readme': role_readme,
                'readme_html': role_html,
                'min_ansible_version': role_min_ansible,
                'company': role_company,
            }

            if dict(this_role.full_metadata) != new_full_metadata:
                this_role.full_metadata = new_full_metadata
                this_role.save()

        next_url = _baseurl + ds.get('next_link')
        if next_url:
            pagenum = int(next_url.split('=')[-1])

    print('STOP LEGACY SYNC!')
