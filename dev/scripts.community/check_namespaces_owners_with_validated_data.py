import datetime
import gzip
import json
import os

from django.contrib.auth import get_user_model

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.utils.namespaces import generate_v3_namespace_from_attributes
from galaxy_ng.app.utils import rbac
from pulp_ansible.app.models import Collection


User = get_user_model()

CHECKMODE = True
if os.environ.get('CHECK_MODE') == "0":
    CHECKMODE = False


class Fixer:

    def __init__(self):
        known_usernames = list(User.objects.values_list('username', flat=True))
        self.known_usernames = dict((x, None) for x in known_usernames)

        known_v1_names = list(LegacyNamespace.objects.values_list('name', flat=True))
        self.known_v1_names = dict((x, None) for x in known_v1_names)

        known_v3_names = list(Namespace.objects.values_list('name', flat=True))
        self.known_v3_names = dict((x, None) for x in known_v3_names)

        collection_namespaces = list(Collection.objects.values_list('namespace', flat=True))
        self.collection_namespaces = sorted(set(collection_namespaces))
        role_namespaces = list(LegacyRole.objects.values_list('namespace__name', flat=True))
        self.role_namespaces = sorted(set(role_namespaces))

        # compressed for size ...
        fn = 'user_namespace_map_validated.json.gz'
        with gzip.open(fn, 'rb') as gz_file:
            raw = gz_file.read()
        self.umap = json.loads(raw)

        self.old_ns_owners = {}
        for k, v in self.umap.items():
            for ns_name in v.get('owned_namespaces', []):
                if ns_name not in self.old_ns_owners:
                    self.old_ns_owners[ns_name] = []
                self.old_ns_owners[ns_name].append(k)

    def changelog(self, msg):
        with open('changelog.txt', 'a') as f:
            f.write(datetime.datetime.now().isoformat() + " " + msg + '\n')

    def match_old_user_to_local_user(self, udata):

        old_username = udata['galaxy_username']
        found_user = User.objects.filter(username=old_username).first()
        if found_user:
            return found_user

        if udata.get('github_login_new'):
            found_user = User.objects.filter(username=udata['github_login_new']).first()
            if found_user:
                return found_user

        if udata.get('github_login'):
            found_user = User.objects.filter(username=udata['github_login']).first()
            if found_user:
                return found_user

        github_login = udata['github_login']
        if udata.get('github_login_new'):
            github_login = udata['github_login_new']
        if github_login is None:
            github_login = udata['galaxy_username']

        print(f'FIX - create user {github_login}')
        self.changelog(f'FIX - create user {github_login}')
        if not CHECKMODE:
            user,_ = User.objects.get_or_create(username=github_login)
            return user

        #import epdb; epdb.st()
        return None

    def do_check(self):

        for ns_name in sorted(list(self.old_ns_owners.keys())):

            print('-' * 50)
            print(ns_name)
            print('-' * 50)

            # optimize ...
            if ns_name not in self.collection_namespaces and ns_name not in self.role_namespaces:
                continue

            # figure this out later ...
            if ns_name not in self.known_v1_names and ns_name not in self.known_v3_names:
                continue

            # figure this out later ...
            is_valid_v3_name = ns_name in self.known_v3_names or ns_name == generate_v3_namespace_from_attributes(username=ns_name)
            if not is_valid_v3_name:
                continue

            v3_namespace = Namespace.objects.filter(name=ns_name).first()
            if not v3_namespace:
                continue

            current_owners = rbac.get_v3_namespace_owners(v3_namespace)
            old_owners = [
                self.match_old_user_to_local_user(self.umap[x])
                for x in self.old_ns_owners[ns_name] if self.umap[x].get('github_login_verified')
            ]
            missing_owners = [x for x in old_owners if x and x not in current_owners]

            #print(ns_name)
            for missing_owner in missing_owners:
                print(f'FIX - add {missing_owner} to v3:{v3_namespace} owners')
                self.changelog(f'FIX - add {missing_owner} to v3:{v3_namespace} owners')
                if not CHECKMODE:
                    rbac.add_user_to_v3_namespace(missing_owner, v3_namespace)


fixer = Fixer()
fixer.do_check()
