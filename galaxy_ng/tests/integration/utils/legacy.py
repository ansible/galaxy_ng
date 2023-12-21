import random
import string
import os
import subprocess
import tempfile
import time
import yaml

from galaxykit.users import delete_user as delete_user_gk
from .client_ansible_lib import get_client
from .namespaces import cleanup_namespace, cleanup_namespace_gk
from .users import (
    delete_group,
    delete_user,
    delete_group_gk,
)


def wait_for_v1_task(task_id=None, resp=None, api_client=None, check=True):

    if task_id is None:
        task_id = resp['task']

    # poll till done or timeout
    poll_url = f'/api/v1/tasks/{task_id}/'

    state = None
    counter = 0
    while state is None or state == 'RUNNING' and counter <= 500:
        counter += 1
        task_resp = api_client(poll_url, method='GET')
        state = task_resp['results'][0]['state']
        if state != 'RUNNING':
            break
        time.sleep(.5)

    if check:
        assert state == 'SUCCESS'

    return task_resp


def clean_all_roles(ansible_config):

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    pre_existing = []
    next_url = '/api/v1/roles/'
    while next_url:
        resp = admin_client(next_url)
        pre_existing.extend(resp['results'])
        if resp['next'] is None:
            break
        next_url = resp['next']
        ix = next_url.index('/api')
        next_url = next_url[ix:]

    # cleanup_social_user would delete these -IF- all
    # are associated to a user but we can't rely on that
    for role_data in pre_existing:
        role_url = f'/api/v1/roles/{role_data["id"]}/'
        try:
            admin_client(role_url, method='DELETE')
        except Exception:
            pass

    usernames = [x['github_user'] for x in pre_existing]
    usernames = sorted(set(usernames))
    for username in usernames:
        cleanup_social_user(username, ansible_config)


def cleanup_social_user(username, ansible_config):
    """ Should delete everything related to a social auth'ed user. """

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    # delete any pre-existing roles from the user
    pre_existing = []
    next_url = f'/api/v1/roles/?owner__username={username}'
    while next_url:
        resp = admin_client(next_url)
        pre_existing.extend(resp['results'])
        if resp['next'] is None:
            break
        next_url = resp['next']
    if pre_existing:
        for pe in pre_existing:
            role_id = pe['id']
            role_url = f'/api/v1/roles/{role_id}/'
            try:
                resp = admin_client(role_url, method='DELETE')
            except Exception:
                pass

    # cleanup the v1 namespace
    resp = admin_client(f'/api/v1/namespaces/?name={username}', method='GET')
    if resp['count'] > 0:
        for result in resp['results']:
            ns_url = f"/api/v1/namespaces/{result['id']}/"
            try:
                admin_client(ns_url, method='DELETE')
            except Exception:
                pass
    resp = admin_client(f'/api/v1/namespaces/?name={username}', method='GET')
    assert resp['count'] == 0

    namespace_name = username.replace('-', '_').lower()

    # cleanup the v3 namespace
    cleanup_namespace(namespace_name, api_client=get_client(config=ansible_config("admin")))

    # cleanup the group
    delete_group(username, api_client=get_client(config=ansible_config("admin")))
    delete_group(
        'namespace:' + namespace_name,
        api_client=get_client(config=ansible_config("admin"))
    )

    # cleanup the user
    delete_user(username, api_client=get_client(config=ansible_config("admin")))


def cleanup_social_user_gk(username, galaxy_client):
    """ Should delete everything related to a social auth'ed user. """

    gc_admin = galaxy_client("admin")

    # delete any pre-existing roles from the user
    pre_existing = []
    next_url = f'/api/v1/roles/?owner__username={username}'
    while next_url:
        resp = gc_admin.get(next_url)
        pre_existing.extend(resp['results'])
        if resp['next'] is None:
            break
        next_url = resp['next']
    if pre_existing:
        for pe in pre_existing:
            role_id = pe['id']
            role_url = f'/api/v1/roles/{role_id}/'
            try:
                resp = gc_admin.delete(role_url)
            except Exception:
                pass

    # cleanup the v1 namespace
    resp = gc_admin.get(f'/api/v1/namespaces/?name={username}')
    if resp['count'] > 0:
        for result in resp['results']:
            ns_url = f"/api/v1/namespaces/{result['id']}/"
            try:
                gc_admin.delete(ns_url)
            except Exception:
                pass
    resp = gc_admin.get(f'/api/v1/namespaces/?name={username}')
    assert resp['count'] == 0

    namespace_name = username.replace('-', '_').lower()

    # cleanup the v3 namespace
    cleanup_namespace_gk(namespace_name, gc_admin)

    # cleanup the group
    delete_group_gk(username, gc_admin)
    delete_group_gk('namespace:' + namespace_name, gc_admin)

    # cleanup the user
    delete_user_gk(gc_admin, username)


def generate_legacy_namespace(exclude=None):
    """ Create a valid random legacy namespace string """

    # This should be a list of pre-existing namespaces
    if exclude is None:
        exclude = []

    def is_valid(ns):
        """ Assert namespace meets backend requirements """
        if ns is None:
            return False
        if ns in exclude:
            return False
        if len(namespace) < 3:
            return False
        if len(namespace) > 64:
            return False
        for char in namespace:
            if char not in string.ascii_lowercase + string.ascii_uppercase + string.digits:
                return False

        return True

    namespace = None
    while not is_valid(namespace):
        namespace = ''
        namespace += random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits)
        for x in range(0, random.choice(range(3, 63))):
            namespace += random.choice(string.ascii_lowercase + string.digits + '_')

    return namespace


def get_all_legacy_namespaces(api_client=None):
    namespaces = []
    next_page = '/api/v1/namespaces/'
    while next_page:
        resp = api_client(next_page)
        namespaces.extend(resp['results'])
        next_page = resp.get('next')
        if next_page:
            # trim the proto+host+port ...
            ix = next_page.index('/api')
            next_page = next_page[ix:]
    return namespaces


def generate_unused_legacy_namespace(api_client=None):
    """ Make a random legacy_namespace string that does not exist """

    assert api_client is not None, "api_client is a required param"
    existing = get_all_legacy_namespaces(api_client=api_client)
    existing = dict((x['name'], x) for x in existing)
    return generate_legacy_namespace(exclude=list(existing.keys()))


class LegacyRoleGitRepoBuilder:

    def __init__(
        self,
        namespace=None,
        name=None,
        meta_namespace=None,
        meta_name=None
    ):
        self.namespace = namespace
        self.name = name
        self.meta_namespace = meta_namespace
        self.meta_name = meta_name

        self.workdir = tempfile.mkdtemp(prefix='gitrepo_')
        self.role_dir = None

        self.role_init()
        self.role_edit()
        self.git_init()
        self.git_commit()

        self.fix_perms()

    def fix_perms(self):
        subprocess.run(f'chown -R pulp:pulp {self.workdir}', shell=True)

    def role_init(self):
        cmd = f'ansible-galaxy role init {self.namespace}.{self.name}'
        self.role_dir = os.path.join(self.workdir, self.namespace + '.' + self.name)
        pid = subprocess.run(cmd, shell=True, cwd=self.workdir)
        assert pid.returncode == 0
        assert os.path.exists(self.role_dir)

    def role_edit(self):
        if self.meta_namespace or self.meta_name:

            meta_file = os.path.join(self.role_dir, 'meta', 'main.yml')
            with open(meta_file, 'r') as f:
                meta = yaml.safe_load(f.read())

            if self.meta_namespace:
                meta['galaxy_info']['namespace'] = self.meta_namespace
            if self.meta_name:
                meta['galaxy_info']['role_name'] = self.meta_name

            with open(meta_file, 'w') as f:
                f.write(yaml.dump(meta))

    def git_init(self):
        subprocess.run('git init', shell=True, cwd=self.role_dir)

    def git_commit(self):

        subprocess.run('git config --global user.email "root@localhost"', shell=True)
        subprocess.run('git config --global user.name "root at localhost"', shell=True)

        subprocess.run('git add *', shell=True, cwd=self.role_dir)
        subprocess.run('git commit -m "first checkin"', shell=True, cwd=self.role_dir)
