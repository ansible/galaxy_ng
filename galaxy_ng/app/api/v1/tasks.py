import copy
import datetime
import logging
import os
import subprocess
import tempfile

from django.db import transaction

from galaxy_importer.config import Config
from galaxy_importer.legacy_role import import_legacy_role

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.utils.galaxy import upstream_role_iterator
from galaxy_ng.app.utils.git import get_tag_commit_hash
from galaxy_ng.app.utils.git import get_tag_commit_date
from galaxy_ng.app.utils.legacy import process_namespace

from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.api.v1.models import LegacyRoleDownloadCount

from git import Repo


logger = logging.getLogger(__name__)


def legacy_role_import(
    request_username=None,
    github_user=None,
    github_repo=None,
    github_reference=None,
    alternate_role_name=None
):
    """
    Import a legacy role by user, repo and or reference.

    :param request_username:
        The username of the person making the import.
    :param github_user:
        The github org or username the role lives in.
    :param github_repo:
        The github repository name that the role lives in.
    :param github_reference:
        A commit, branch or tag name to import.
    :param alternate_role_name:
        Override the enumerated role name when the repo does
        not conform to the ansible-role-<name> convention.

    This function attempts to clone the github repository to a
    temporary directory and uses galaxy-importer functions to
    enumerate the metadata and doc strings. If the role already
    exists in the database, the code will attempt to add a new
    version to the full_metadata. Roles can be versionless so
    there will not be any duplicate key errors. However,
    the "commit" field should always reflect the latest import.
    """
    logger.debug('START LEGACY ROLE IMPORT')

    # prevent empty strings?
    if not github_reference:
        github_reference = None

    # this shouldn't happen but just in case ...
    if request_username and not User.objects.filter(username=request_username).exists():
        raise Exception(f'Username {request_username} does not exist in galaxy')

    # the user should have a legacy and v3 namespace if they logged in ...
    namespace = LegacyNamespace.objects.filter(name=github_user).first()
    if not namespace:
        raise Exception(f'No legacy namespace exists for {github_user}')

    # we have to have a v3 namespace because of the rbac based ownership ...
    v3_namespace = namespace.namespace
    if not v3_namespace:
        raise Exception(f'No v3 namespace exists for {github_user}')

    with tempfile.TemporaryDirectory() as tmp_path:
        # galaxy-importer requires importing legacy roles from the role's parent directory.
        os.chdir(tmp_path)

        # galaxy-importer wants the role's directory to be the name of the role.
        checkout_path = os.path.join(tmp_path, github_repo)
        clone_url = f'https://github.com/{github_user}/{github_repo}'

        # pygit didn't have an obvious way to prevent interactive clones ...
        pid = subprocess.run(
            f'GIT_TERMINAL_PROMPT=0 git clone --recurse-submodules {clone_url} {checkout_path}',
            shell=True,
        )
        if pid.returncode != 0:
            raise Exception(f'git clone for {clone_url} failed')

        # bind the checkout to a pygit object
        gitrepo = Repo(checkout_path)

        github_commit = None
        github_commit_date = None

        if github_reference is not None:
            gitrepo.checkout(github_reference)
            github_commit = get_tag_commit_hash(
                clone_url,
                github_reference,
                checkout_path=checkout_path
            )
            github_commit_date = get_tag_commit_date(
                clone_url,
                github_reference,
                checkout_path=checkout_path
            )
        else:
            # FIXME - figure out the old logic.
            if gitrepo.tags:
                tag = gitrepo.tags[-1]
                github_reference = tag.name
                github_commit = tag.commit.hexsha
                github_commit_date = datetime.datetime.fromtimestamp(tag.commit.committed_date)
                github_commit_date = github_commit_date.isoformat()

        logger.debug(f'GITHUB_REFERENCE: {github_reference}')
        logger.debug(f'GITHUB_COMMIT: {github_commit}')

        # Parse legacy role with galaxy-importer.
        importer_config = Config()
        result = import_legacy_role(checkout_path, namespace.name, importer_config, logger)
        galaxy_info = result["metadata"]["galaxy_info"]
        logger.debug(f"TAGS: {galaxy_info['galaxy_tags']}")

        role_name = result["name"] or alternate_role_name or \
            github_repo.replace("ansible-role-", "")

        # check if this namespace/name/version has already been imported
        old = LegacyRole.objects.filter(namespace=namespace, name=role_name).first()
        if old is not None:
            old_versions = old.full_metadata.get('versions', [])
            old_versions = [x['name'] for x in old_versions]
            logger.debug(f'OLD VERSIONS: {old_versions}')
            if github_reference in old_versions:
                msg = (
                    f'{namespace.name}.{role_name} {github_reference}'
                    + ' has already been imported'
                )
                raise Exception(msg)

        new_full_metadata = {
            'imported': datetime.datetime.now().isoformat(),
            'clone_url': clone_url,
            'tags': galaxy_info["galaxy_tags"],
            'commit': github_commit,
            'github_repo': github_repo,
            'github_reference': github_reference,
            'issue_tracker_url': galaxy_info["issue_tracker_url"] or clone_url + "/issues",
            'dependencies': result["metadata"]["dependencies"],
            'versions': [],
            'description': galaxy_info["description"] or "",
            'license': galaxy_info["license"] or "",
            'min_ansible_version': galaxy_info["min_ansible_version"] or "",
            'min_ansible_container_version': galaxy_info["min_ansible_container_version"] or "",
            'platforms': galaxy_info["platforms"],
            'readme': result["readme_file"],
            'readme_html': result["readme_html"]
        }

        # Make the object
        this_role, _ = LegacyRole.objects.get_or_create(
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

    logger.debug('STOP LEGACY ROLE IMPORT')
    return True


def legacy_sync_from_upstream(
    baseurl=None,
    github_user=None,
    role_name=None,
    role_version=None,
    limit=None,
    start_page=None,
):
    """
    Sync legacy roles from a remote v1 api.

    :param baseurl:
        Allow the client to override the upstream v1 url this task will sync from.
    :param github_user:
        Allow the client to reduce the set of synced roles by the username.
    :param role_name:
        Allow the client to reduce the set of synced roles by the role name.
    :param limit:
        Allow the client to reduce the total number of synced roles.

    This is conceptually similar to the pulp_ansible/app/tasks/roles.py:synchronize
    function but has more robust handling and better schema matching. Although
    not considered something we'd be normally running on a production hosted
    galaxy instance, it is necessary for mirroring the roles into that future
    system until it is ready to deprecate the old instance.
    """

    logger.debug(
        'STARTING LEGACY SYNC!'
        + f' {baseurl} {github_user} {role_name} {role_version} {limit}'
    )

    logger.debug('SYNC INDEX EXISTING NAMESPACES')
    nsmap = {}

    # allow the user to specify how many roles to sync
    if limit is not None:
        limit = int(limit)

    # index of all roles
    rmap = {}

    iterator_kwargs = {
        'baseurl': baseurl,
        'github_user': github_user,
        'role_name': role_name,
        'limit': limit,
        'start_page': start_page,
    }
    for ns_data, rdata, rversions in upstream_role_iterator(**iterator_kwargs):

        # processing a namespace should make owners and set rbac as needed ...
        if ns_data['name'] not in nsmap:
            namespace, v3_namespace = process_namespace(ns_data['name'], ns_data)
            nsmap[ns_data['name']] = (namespace, v3_namespace)
        else:
            namespace, v3_namespace = nsmap[ns_data['name']]

        ruser = rdata.get('github_user')
        rname = rdata.get('name')

        logger.info(f'POPULATE {ruser}.{rname}')

        rkey = (ruser, rname)
        remote_id = rdata['id']
        role_versions = rversions[:]
        github_repo = rdata['github_repo']
        github_branch = rdata['github_branch']
        clone_url = f'https://github.com/{ruser}/{github_repo}'
        sfields = rdata.get('summary_fields', {})
        role_tags = sfields.get('tags', [])
        commit_hash = rdata.get('commit')
        commit_msg = rdata.get('commit_message')
        commit_url = rdata.get('commit_url')
        issue_tracker = rdata.get('issue_tracker_url', clone_url + '/issues')
        # role_versions = sfields.get('versions', [])
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
        role_download_count = rdata.get('download_count', 0)

        if rkey not in rmap:
            logger.debug(f'SYNC create initial role for {rkey}')
            this_role, _ = LegacyRole.objects.get_or_create(
                namespace=namespace,
                name=rname
            )
            rmap[rkey] = this_role
        else:
            this_role = rmap[rkey]

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
            # 'github_reference': github_reference,
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
            with transaction.atomic():
                this_role.full_metadata = new_full_metadata
                this_role.save()

        with transaction.atomic():
            counter, _ = LegacyRoleDownloadCount.objects.get_or_create(legacyrole=this_role)
            counter.count = role_download_count
            counter.save()

    logger.debug('STOP LEGACY SYNC!')
