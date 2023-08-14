"""Utility functions for AH tests."""

import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import json
import time
import uuid
from typing import List, Union
from ansible.galaxy.api import _urljoin

import yaml
from urllib.parse import urljoin
from urllib.parse import urlparse
from contextlib import contextmanager

from ansible.galaxy.api import GalaxyError
from orionutils.generator import build_collection as _build_collection
from orionutils.generator import randstr

from galaxy_ng.tests.integration.constants import USERNAME_PUBLISHER
from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_ONETIME

from .tasks import wait_for_task
from .urls import wait_for_url
from .tools import iterate_all

try:
    import importlib.resources as pkg_resources
except ModuleNotFoundError:
    import importlib_resources as pkg_resources

logger = logging.getLogger(__name__)


class ArtifactFile:
    """Shim to emulate the return object from orionutils.build."""
    def __init__(self, fn, namespace=None, name=None, version=None, key=None):
        self.filename = fn
        self.namespace = namespace
        self.name = name
        self.version = version
        self.key = key


def build_collection(
    base=None,
    config=None,
    filename=None,
    key=None,
    pre_build=None,
    extra_files=None,
    namespace=None,
    name=None,
    tags=None,
    version=None,
    dependencies=None,
    requires_ansible='>=2.13.0',
    roles=['docker_role'],
    # use_orionutils=True
    use_orionutils=False
) -> ArtifactFile:

    """Assemble a collection tarball from given parameters.

    Use the ansible-galaxy cli to init and build a collection artifact.

    Args:
        base: the template for orion to use (default to "skeleton")
        config: a mapping for most other args
        filename: use an alternate filename for the artifact
        key: used to add entropy to the collection name
        pre_build: ?
        extra_files: a dict with filenames as the key and content as the value
        namespace: collection namespace (USERNAME_PUBLISHER by default)
        name: collection name (random by default)
        tags: tags to add to galaxy.yml
        version: semantic version string
        dependencies: a list of dependencies
        requires_ansible: this yaml'ized string will go into meta/requirements.yml
        use_orionurls: defer building to orionutils or not

    Returns:
        An "ArtifactFile" object with the tarball filename set as the .filename
    """

    if base is None:
        base = "skeleton"

    if config is None:
        config = {
            "namespace": None,
            "name": None,
            "version": None,
            "tags": []
        }

    # use order of precedence to set the config ...
    for ckey in ['namespace', 'name', 'version', 'dependencies', 'tags']:
        if ckey in locals() and locals()[ckey] is not None:
            config[ckey] = locals()[ckey]
        elif config.get(ckey):
            pass
        else:
            if ckey == 'namespace':
                config[ckey] = USERNAME_PUBLISHER
            elif ckey == 'name':
                config[ckey] = randstr()
            elif ckey == 'version':
                config[ckey] = '1.0.0'

    # workaround for cloud importer config
    if 'tools' not in config['tags']:
        config['tags'].append('tools')

    # https://github.com/peaqe/orion-utils/blob/master/orionutils/generator.py#L147
    if use_orionutils:
        return _build_collection(
            base,
            config=config,
            filename=filename,
            key=key,
            pre_build=pre_build,
            extra_files=extra_files
        )

    # orionutils uses the key to prefix the name
    if key is not None:
        name = config['name'] + "_" + key
        config['name'] = name

    # use galaxy cli to build it ...
    dstdir = tempfile.mkdtemp(prefix='collection-artifact-')
    dst = None
    with tempfile.TemporaryDirectory(prefix='collection-build-') as tdir:

        basedir = os.path.join(tdir, config['namespace'], config['name'])
        rolesdir = os.path.join(basedir, 'roles')

        # init the skeleton ...
        cmd = f"ansible-galaxy collection init {config['namespace']}.{config['name']}"
        pid = subprocess.run(
            cmd,
            shell=True,
            cwd=tdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        assert pid.returncode == 0, str(pid.stdout.decode('utf-8')) \
            + str(pid.stderr.decode('utf-8'))

        # make roles ...
        if roles:
            for role_name in roles:
                cmd = f"ansible-galaxy role init {role_name}"
                pid2 = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=rolesdir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                assert pid2.returncode == 0, str(pid2.stdout.decode('utf-8')) \
                    + str(pid2.stderr.decode('utf-8'))

        # fix galaxy.yml
        galaxy_file = os.path.join(basedir, 'galaxy.yml')
        with open(galaxy_file, 'r') as f:
            meta = yaml.safe_load(f.read())
        meta.update(config)
        with open(galaxy_file, 'w') as f:
            f.write(yaml.dump(meta))

        # need the meta/runtime.yml file ...
        if requires_ansible is not None:
            meta_dir = os.path.join(basedir, 'meta')
            if not os.path.exists(meta_dir):
                os.makedirs(meta_dir)
            runtime_file = os.path.join(meta_dir, 'runtime.yml')
            with open(runtime_file, 'w') as f:
                f.write(yaml.dump({'requires_ansible': requires_ansible}))

        # need a CHANGELOG file ...
        with open(os.path.join(basedir, 'CHANGELOG.md'), 'w') as f:
            f.write('')

        if extra_files:
            for ename, econtent in extra_files.items():
                fpath = os.path.join(basedir, ename)
                fdir = os.path.dirname(fpath)
                if not os.path.exists(fdir):
                    os.makedirs(fdir)
                with open(fpath, 'w') as f:
                    if isinstance(econtent, dict) and econtent.get('mimetype') == 'yaml':
                        yaml.dump(econtent['content'], f)
                    elif isinstance(econtent, dict):
                        f.write(econtent['content'])
                    else:
                        f.write(econtent)

        if pre_build:
            raise Exception('pre_build not yet implemented')

        # build it
        cmd = "ansible-galaxy collection build ."
        pid3 = subprocess.run(
            cmd,
            shell=True,
            cwd=basedir,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        assert pid3.returncode == 0, str(pid3.stdout.decode('utf-8')) \
            + str(pid3.stderr.decode('utf-8'))
        fn = pid3.stdout.decode('utf-8').strip().split('\n')[-1].split()[-1]

        # Copy to permanent location
        dst = os.path.join(dstdir, os.path.basename(fn))
        shutil.copy(fn, dst)

        if filename:
            raise Exception('filename not yet implemented')

    return ArtifactFile(
        dst,
        namespace=config['namespace'],
        name=config['name'],
        version=config['version'],
        key=key
    )


def upload_artifact(
    config, client, artifact, hash=True, no_filename=False, no_file=False, use_distribution=False
):
    """
    Publishes a collection to a Galaxy server and returns the import task URI.

    :param config: The ansibleconfig object.
    :param client: The galaxyclient object.
    :param artifact: The artifact object.
    :param hash: compute and send a sha256 sum for the payload.
    :param no_filename: Skip sending the filename in the form.
    :param no_file: Skip sneding the file in the form.
    :param use_distribution: If true, upload to the inbound-<namespace> endpoint.
    :return: The import task URI that contains the import results.
    """
    collection_path = artifact.filename
    with open(collection_path, "rb") as collection_tar:
        data = collection_tar.read()

    def to_bytes(s, errors=None):
        return s.encode("utf8")

    boundary = "--------------------------%s" % uuid.uuid4().hex
    file_name = os.path.basename(collection_path)
    part_boundary = b"--" + to_bytes(boundary, errors="surrogate_or_strict")

    from ansible.galaxy.api import _urljoin
    from ansible.utils.hashing import secure_hash_s

    form = []

    if hash:
        if isinstance(hash, bytes):
            b_hash = hash
        else:
            from hashlib import sha256

            b_hash = to_bytes(secure_hash_s(data, sha256), errors="surrogate_or_strict")
        form.extend([part_boundary, b'Content-Disposition: form-data; name="sha256"', b_hash])

    if not no_file:
        if no_filename:
            form.extend(
                [
                    part_boundary,
                    b'Content-Disposition: file; name="file"',
                    b"Content-Type: application/octet-stream",
                ]
            )
        else:
            form.extend(
                [
                    part_boundary,
                    b'Content-Disposition: file; name="file"; filename="%s"' % to_bytes(file_name),
                    b"Content-Type: application/octet-stream",
                ]
            )
    else:
        form.append(part_boundary)

    form.extend([b"", data, b"%s--" % part_boundary])

    data = b"\r\n".join(form)

    headers = {
        "Content-type": "multipart/form-data; boundary=%s" % boundary,
        "Content-length": len(data),
    }

    n_url = ""
    if use_distribution:
        n_url = (
            _urljoin(
                config["url"],
                "content",
                f"inbound-{artifact.namespace}",
                "v3",
                "artifacts",
                "collections",
            )
            + "/"
        )
    else:
        n_url = _urljoin(config["url"], "v3", "artifacts", "collections") + "/"

    resp = client(n_url, args=data, headers=headers, method="POST", auth_required=True)

    return resp


@contextmanager
def modify_artifact(artifact):
    filename = artifact.filename
    with tempfile.TemporaryDirectory() as dirpath:
        # unpack
        tf = tarfile.open(filename)
        tf.extractall(dirpath)

        try:
            yield dirpath

        finally:
            # re-pack
            tf = tarfile.open(filename, "w:gz")
            for name in os.listdir(dirpath):
                tf.add(os.path.join(dirpath, name), name)
            tf.close()


def get_collections_namespace_path(namespace):
    """Get collections namespace path."""
    return os.path.expanduser(f"~/.ansible/collections/ansible_collections/{namespace}/")


def get_collection_full_path(namespace, collection_name):
    """Get collections full path."""
    return os.path.join(get_collections_namespace_path(namespace), collection_name)


def set_certification(client, collection, level="published", hub_4_5=False):
    """Moves a collection from the `staging` to the `published` repository.

    For use in instances that use repository-based certification and that
    do not have auto-certification enabled.
    """

    if hub_4_5:
        if client.config["use_move_endpoint"]:
            url = (
                f"v3/collections/{collection.namespace}/{collection.name}/versions/"
                f"{collection.version}/move/staging/published/"
            )
            client(url, method="POST", args=b"{}")
            dest_url = (
                f"v3/collections/{collection.namespace}/"
                f"{collection.name}/versions/{collection.version}/"
            )
            return wait_for_url(client, dest_url)

    # exit early if config is set to auto approve
    if not client.config["use_move_endpoint"]:
        return

    # check if artifact is in staging repo, if not wait
    staging_artifact_url = (
        f"v3/plugin/ansible/content/staging/collections/index/"
        f"{collection.namespace}/{collection.name}/versions/{collection.version}/"
    )
    wait_for_url(client, staging_artifact_url)

    if client.config["upload_signatures"]:
        # Write manifest to temp file
        tf = tarfile.open(collection.filename, mode="r:gz")
        tdir = tempfile.TemporaryDirectory()
        keyring = tempfile.NamedTemporaryFile("w")
        tf.extract("MANIFEST.json", tdir.name)

        # Setup local keystore
        # gpg --no-default-keyring --keyring trustedkeys.gpg
        # gpg --import clowder-data.key
        with pkg_resources.path("dev.data", "ansible-sign.gpg") as keyfilename:
            subprocess.run(
                [
                    "gpg",
                    "--quiet",
                    "--batch",
                    "--pinentry-mode",
                    "loopback",
                    "--yes",
                    "--no-default-keyring",
                    "--keyring",
                    keyring.name,
                    "--import",
                    keyfilename,
                ]
            )

        # Run gpg to generate signature
        with pkg_resources.path("dev.data", "collection_sign.sh") as collection_sign:
            result = subprocess.check_output(
                [collection_sign, os.path.join(tdir.name, "MANIFEST.json")],
                env={
                    "KEYRING": keyring.name,
                },
            )
            signature_filename = json.loads(result)["signature"]

        # Prepare API endpoint URLs needed to POST signature
        sig_url = urljoin(
            client.config["url"],
            "pulp/api/v3/content/ansible/collection_signatures/",
        )
        rep_obj_url = urljoin(
            client.config["url"],
            "pulp/api/v3/repositories/ansible/ansible/?name=staging",
        )
        repository_pulp_href = client(rep_obj_url)["results"][0]["pulp_href"]

        artifact_obj_url = f"_ui/v1/repo/staging/{collection.namespace}/" f"{collection.name}/"
        all_versions = client(artifact_obj_url)["all_versions"]
        one_version = [v for v in all_versions if v["version"] == collection.version][0]
        artifact_pulp_id = one_version["id"]
        # FIXME: used unified uirl join utility below
        artifact_pulp_href = (
            "/"
            + _urljoin(
                urlparse(client.config["url"]).path,
                "pulp/api/v3/content/ansible/collection_versions/",
                artifact_pulp_id,
            )
            + "/"
        )

        data = {
            "repository": repository_pulp_href,
            "signed_collection": artifact_pulp_href,
        }
        kwargs = setup_multipart(signature_filename, data)
        resp = client(sig_url, method="POST", auth_required=True, **kwargs)
        wait_for_task(client, resp)

    # move the artifact from staging to destination repo
    url = (
        f"v3/collections/{collection.namespace}/{collection.name}/versions/"
        f"{collection.version}/move/staging/{level}/"
    )
    job_tasks = client(url, method="POST", args=b"{}")
    assert "copy_task_id" in job_tasks
    assert "remove_task_id" in job_tasks

    # wait for each unique task to finish ...
    for key in ["copy_task_id", "remove_task_id"]:
        task_id = job_tasks.get(key)

        # The task_id is not a url, so it has to be assembled from known data ...
        # http://.../api/automation-hub/pulp/api/v3/tasks/8be0b9b6-71d6-4214-8427-2ecf81818ed4/
        ds = {"task": f"{client.config['url']}/pulp/api/v3/tasks/{task_id}"}
        task_result = wait_for_task(client, ds)
        assert task_result["state"] == "completed", task_result

    # callers expect response as part of this method, ensure artifact is there
    dest_url = (
        f"v3/plugin/ansible/content/{level}/collections/index/"
        f"{collection.namespace}/{collection.name}/versions/{collection.version}/"
    )
    return wait_for_url(client, dest_url)


def copy_collection_version(client, collection, src_repo_name, dest_repo_name):
    """Copies a collection from the `src_repo` to the src_repo to dest_repo."""
    url = (
        f"v3/collections/{collection.namespace}/{collection.name}/versions/"
        f"{collection.version}/copy/{src_repo_name}/{dest_repo_name}/"
    )
    job_tasks = client(url, method="POST", args=b"{}")
    assert 'task_id' in job_tasks

    # await task completion

    task_id = job_tasks.get("task_id")

    # The task_id is not a url, so it has to be assembled from known data ...
    # http://.../api/automation-hub/pulp/api/v3/tasks/8be0b9b6-71d6-4214-8427-2ecf81818ed4/
    ds = {
        'task': f"{client.config['url']}/pulp/api/v3/tasks/{task_id}"
    }
    task_result = wait_for_task(client, ds)
    assert task_result['state'] == 'completed', task_result

    # callers expect response as part of this method, ensure artifact is there
    dest_url = (
        f"v3/plugin/ansible/content/{dest_repo_name}/collections/index/"
        f"{collection.namespace}/{collection.name}/versions/{collection.version}/"
    )
    return wait_for_url(client, dest_url)


def get_all_collections_by_repo(api_client=None):
    """ Return a dict of each repo and their collections """
    assert api_client is not None, "api_client is a required param"
    api_prefix = api_client.config.get("api_prefix").rstrip("/")
    collections = {
        'staging': {},
        'published': {},
        'community': {},
        'rh-certified': {},
    }
    for repo in collections.keys():
        next_page = f'{api_prefix}/_ui/v1/collection-versions/?repository={repo}'
        while next_page:
            resp = api_client(next_page)
            for _collection in resp['data']:
                key = (
                    _collection['namespace'],
                    _collection['name'],
                    _collection['version']
                )
                collections[repo][key] = _collection
            next_page = resp.get('links', {}).get('next')
    return collections


def get_all_repository_collection_versions(api_client):
    """ Return a dict of each repo and their collection versions """

    assert api_client is not None, "api_client is a required param"
    api_prefix = api_client.config.get("api_prefix").rstrip("/")

    repositories = [
        'staging',
        'published',
        # 'verified',
        # 'community'
    ]

    collections = []
    for repo in repositories:
        next_page = f'{api_prefix}/content/{repo}/v3/collections/'
        while next_page:
            resp = api_client(next_page)
            collections.extend(resp['data'])
            next_page = resp.get('links', {}).get('next')

    collection_versions = []
    for collection in collections:
        next_page = collection['versions_url']
        while next_page:
            resp = api_client(next_page)
            for cv in resp['data']:
                cv['namespace'] = collection['namespace']
                cv['name'] = collection['name']
                if 'staging' in cv['href']:
                    cv['repository'] = 'staging'
                elif 'published' in cv['href']:
                    cv['repository'] = 'published'
                elif 'verified' in cv['href']:
                    cv['repository'] = 'verified'
                elif 'community' in cv['href']:
                    cv['repository'] = 'community'
                else:
                    cv['repository'] = None
                collection_versions.append(cv)
            next_page = resp.get('links', {}).get('next')

    rcv = dict(
        (
            (x['repository'], x['namespace'], x['name'], x['version']),
            x
        )
        for x in collection_versions
    )
    return rcv


def delete_all_collections(api_client):
    """Deletes all collections regardless of dependency chains."""

    api_prefix = api_client.config.get("api_prefix").rstrip("/")

    # iterate until none are left
    while True:
        cvs = get_all_repository_collection_versions(api_client)
        cvs = list(cvs.keys())
        if len(cvs) == 0:
            break

        # make repo+collection keys
        delkeys = [(x[0], x[1], x[2]) for x in cvs]
        delkeys = sorted(set(delkeys))

        # try to delete each one
        for delkey in delkeys:
            crepo = delkey[0]
            namespace_name = delkey[1]
            cname = delkey[2]

            # if other collections require this one, the delete will fail
            resp = None
            try:
                resp = api_client(
                    (f'{api_prefix}/v3/plugin/ansible/content'
                        f'/{crepo}/collections/index/{namespace_name}/{cname}/'),
                    method='DELETE'
                )
            except GalaxyError:
                pass

            if resp is not None:
                wait_for_task(api_client, resp, timeout=10000)


def delete_all_collections_in_namespace(api_client, namespace_name):

    assert api_client is not None, "api_client is a required param"

    # accumlate a list of matching collections in each repo
    ctuples = set()
    cmap = get_all_collections_by_repo(api_client)
    for repo, cvs in cmap.items():
        for cv_spec in cvs.keys():
            if cv_spec[0] == namespace_name:
                ctuples.add((repo, cv_spec[0], cv_spec[1]))

    # delete each collection ...
    for ctuple in ctuples:
        crepo = ctuple[0]
        cname = ctuple[2]

        recursive_delete(api_client, namespace_name, cname, crepo)


def recursvive_delete(api_client, namespace_name, cname, crepo):
    return recursive_delete(api_client, namespace_name, cname, crepo)


def recursive_delete(api_client, namespace_name, cname, crepo):
    """Recursively delete a collection along with every other collection that depends on it."""
    api_prefix = api_client.config.get("api_prefix").rstrip("/")

    dependants = set([
        (cv["namespace"], cv["name"]) for cv in iterate_all(
            api_client,
            f"_ui/v1/collection-versions/?dependency={namespace_name}.{cname}"
        )
    ])

    if dependants:
        for ns, name in dependants:
            recursvive_delete(api_client, ns, name, crepo)

    # Try deleting the whole collection ...
    try:
        resp = api_client(
            (f'{api_prefix}/v3/plugin/ansible/content'
                f'/{crepo}/collections/index/{namespace_name}/{cname}/'),
            method='DELETE'
        )
    except GalaxyError as ge:
        if ge.http_code in [404]:
            return
    # wait for the orphan_cleanup job to finish ...
    try:
        wait_for_task(api_client, resp, timeout=10000)
    except GalaxyError as ge:
        # FIXME - pulp tasks do not seem to accept token auth
        if ge.http_code in [403, 404]:
            time.sleep(SLEEP_SECONDS_ONETIME)
        else:
            raise Exception(ge)


def setup_multipart(path: str, data: dict) -> dict:
    buffer = []
    boundary = b"--" + uuid.uuid4().hex.encode("ascii")
    filename = os.path.basename(path)
    # part_boundary = b'--' + to_bytes(boundary)

    buffer += [
        boundary,
        b'Content-Disposition: file; name="file"; filename="%s"' % filename.encode("ascii"),
        b"Content-Type: application/octet-stream",
    ]
    buffer += [
        b"",
        open(path, "rb").read(),
    ]

    for name, value in data.items():
        add_multipart_field(boundary, buffer, name, value)

    buffer += [
        boundary + b"--",
    ]

    data = b"\r\n".join(buffer)
    headers = {
        "Content-type": "multipart/form-data; boundary=%s"
        % boundary[2:].decode("ascii"),  # strip --
        "Content-length": len(data),
    }

    return {
        "args": data,
        "headers": headers,
    }


def add_multipart_field(
    boundary: bytes, buffer: List[bytes], name: Union[str, bytes], value: Union[str, bytes]
):
    if isinstance(name, str):
        name = name.encode("utf8")
    if isinstance(value, str):
        value = value.encode("utf8")
    buffer += [
        boundary,
        b'Content-Disposition: form-data; name="%s"' % name,
        b"Content-Type: text/plain",
        b"",
        value,
    ]
