import datetime
import glob
import os
import subprocess
import yaml


def get_path_git_root(path):
    """ Find the root of a checkout path """
    cmd = 'git rev-parse --show-toplevel'
    pid = subprocess.run(cmd, cwd=path, shell=True, stdout=subprocess.PIPE)
    return pid.stdout.decode('utf-8').strip()


def get_path_head_date(path):
    """ Get the timestamp of the HEAD commit """
    cmd = 'git log -1 --format="%ci"'
    pid = subprocess.run(cmd, cwd=path, shell=True, stdout=subprocess.PIPE)
    ds = pid.stdout.decode('utf-8').strip()

    # 2021-10-31 00:03:43 -0500
    ts = datetime.datetime.strptime(ds, '%Y-%m-%d %H:%M:%S %z')
    return ts


def get_path_role_repository(path):
    """ Get the repository url for a checkout """
    cmd = "git remote -v | head -1 | awk '{print $2}'"
    pid = subprocess.run(cmd, cwd=path, shell=True, stdout=subprocess.PIPE)
    origin = pid.stdout.decode('utf-8').strip()
    return origin


def get_path_role_meta(path):
    """ Retrive the meta/main.yml from a role """
    metaf = os.path.join(path, 'meta', 'main.yml')
    with open(metaf, 'r') as f:
        meta = yaml.safe_load(f.read())
    return meta


def get_path_role_name(path):
    """ Enumerate the name of a role from a checkout """
    name = get_path_galaxy_key(path, 'name')
    if name is not None:
        return name

    metaf = os.path.join(path, 'meta', 'main.yml')
    meta = None
    if os.path.exists(metaf):
        with open(metaf, 'r') as f:
            meta = yaml.safe_load(f.read())

    if meta and 'role_name' in meta['galaxy_info']:
        name = meta['galaxy_info']['role_name']
    else:
        cmd = "git remote -v | head -1 | awk '{print $2}'"
        pid = subprocess.run(cmd, cwd=path, shell=True, stdout=subprocess.PIPE)
        origin = pid.stdout.decode('utf-8').strip()
        name = origin.replace('https://github.com/', '').split('/')[1]

        if 'ansible-role-' in name:
            name = name.replace('ansible-role-', '')
        if name.startswith('ansible-'):
            name = name.replace('ansible-', '')
        if name.endswith('-ansible'):
            name = name.replace('-ansible', '')
        if name.startswith('ansible.'):
            name = name.replace('ansible.', '')

    # https://github.com/angstwad/docker.ubuntu -> docker_ubuntu
    if '.' in name:
        name = name.replace('.', '_')

    #  https://github.com/sbaerlocher/ansible.update-management -> update_management
    if '-' in name:
        name = name.replace('-', '_')

    return name


def get_path_role_namespace(path):
    """ Enumerate the github_user/namespace from a role checkout """
    namespace = get_path_galaxy_key(path, 'namespace')
    if namespace is not None:
        return namespace

    cmd = "git remote -v | head -1 | awk '{print $2}'"
    pid = subprocess.run(cmd, cwd=path, shell=True, stdout=subprocess.PIPE)
    origin = pid.stdout.decode('utf-8').strip()
    namespace = origin.replace('https://github.com/', '').split('/')[0]

    if namespace == 'ansible-collections':
        namespace = 'ansible'

    return namespace


def get_path_role_version(path):
    """ Enumerate the version of a role """
    version = get_path_galaxy_key(path, 'version')
    if version is not None:
        return version

    # This is a shim to force semantic version
    ds = get_path_head_date(path)
    parts = ds.isoformat().split('T')
    ymd = parts[0].split('-')
    ts = parts[1].replace(':', '')
    ts = ts.replace('-', '')
    ts = ts.replace('+', '')
    version = '1.0.0' + '+' + ymd[0] + ymd[1] + ymd[2] + ts

    return version


def path_is_role(path):
    """ Detect if a path is a role or not """
    namespace = get_path_galaxy_key(path, 'namespace')
    name = get_path_galaxy_key(path, 'name')
    if namespace is not None and name is not None:
        return False

    paths = glob.glob(f'{path}/*')
    paths = [os.path.basename(x) for x in paths]

    if 'plugins' in paths:
        return False

    if 'tasks' in paths:
        return True

    if 'library' in paths:
        return True

    if 'handlers' in paths:
        return True

    if 'defaults' in paths:
        return True

    return False


def make_runtime_yaml(path):
    """ Generate a runtime.yml for a collection """
    metadir = os.path.join(path, 'meta')
    runtimef = os.path.join(metadir, 'runtime.yml')

    if not os.path.exists(metadir):
        os.makedirs(metadir)

    data = {'requires_ansible': '>=2.10'}

    with open(runtimef, 'w') as f:
        yaml.dump(data, f)


def get_path_galaxy_key(path, key):
    """ Retrieve a specific key from galaxy.yml """
    gfn = os.path.join(path, 'galaxy.yml')
    if not os.path.exists(gfn):
        return None

    with open(gfn, 'r') as f:
        ds = yaml.safe_load(f.read())

    return ds.get(key)


def set_path_galaxy_key(path, key, value):
    """ Set a specific key in a galaxy.yml """
    gfn = os.path.join(path, 'galaxy.yml')
    with open(gfn, 'r') as f:
        ds = yaml.safe_load(f.read())

    ds[key] = value
    with open(gfn, 'w') as f:
        yaml.dump(ds, f)


def set_path_galaxy_version(path, version):
    """ Set the version in galaxy.yml """
    set_path_galaxy_key(path, 'version', version)


def set_path_galaxy_repository(path, repository):
    """ Set the repository in galaxy.yml """
    set_path_galaxy_key(path, 'repository', repository)
