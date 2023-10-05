import gzip
import json
import os

from django.contrib.auth import get_user_model

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.utils.namespaces import generate_v3_namespace_from_attributes
from galaxy_ng.app.utils import rbac


User = get_user_model()


def do_check():

    checkmode = True
    if os.environ.get('CHECK_MODE') == "0":
        checkmode = False

    known_usernames = list(User.objects.values_list('username', flat=True))
    known_usernames = dict((x, None) for x in known_usernames)

    known_v1_names = list(LegacyNamespace.objects.values_list('name', flat=True))
    known_v1_names = dict((x, None) for x in known_v1_names)

    known_v3_names = list(Namespace.objects.values_list('name', flat=True))
    known_v3_names = dict((x, None) for x in known_v3_names)

    # compressed for size ...
    fn = 'user_namespace_map_validated.json.gz'
    with gzip.open(fn, 'rb') as gz_file:
        raw = gz_file.read()
    umap = json.loads(raw)

    # check each upstream user one by one ...
    uids = list(umap.keys())
    uids = sorted(uids, key=lambda x: int(x))
    for uid in uids:
        old_data = umap[uid]
        print(f"{uid} {old_data['galaxy_username']}")

        # worry about these later ...
        if not old_data.get('github_login_verified'):
            continue

        # worry about these later ...
        if old_data['galaxy_username'] != old_data['github_login'] or \
            (old_data.get('gitub_login_new') and old_data.get('gitub_login_new') != old_data['galaxy_username']):
            continue

        # skip any users that have no current namespaces on this system ...
        # this should theoretically skip making namespaces with no content
        found_namespaces = [x for x in old_data.get('owned_namespaces', []) if x in known_v1_names or x in known_v3_names]
        if not found_namespaces:
            continue

        galaxy_username = old_data['galaxy_username']
        github_login = old_data['github_login']
        github_id = old_data['github_id']
        if old_data['github_login_new']:
            github_login = old_data['github_login_new']

        # find or make the user ...
        found_user = User.objects.filter(username=galaxy_username).first()
        if not found_user:
            print(f'\tFIX - create user {galaxy_username}')
            if not checkmode:
                print(f'\t\tcheckmode:{checkmode} do user create ...')
                found_user, _ = User.objects.get_or_create(username=galaxy_username)
            else:
                continue

        # check each owned namespace (v1+v3) ...
        for ns_name in old_data.get('owned_namespaces', []):
            found_v1_namespace = LegacyNamespace.objects.filter(name=ns_name).first()
            if not found_v1_namespace:
                print(f'\tFIX - create legacy namespace {ns_name}')
                if not checkmode:
                    print(f'\t\tcheckmode:{checkmode} do legacy ns create ...')
                    found_v1_namespace,_ = LegacyNamespace.objects.get_or_create(name=ns_name)
                else:
                    continue

            # the v3 namespace has to be valid ...
            v3_ns_name = generate_v3_namespace_from_attributes(username=ns_name)
            # print(f'\tv3:{v3_ns_name}')

            found_v3_namespace = Namespace.objects.filter(name=v3_ns_name).first()
            if not found_v3_namespace:
                print(f'\tFIX - create v3 namespace {v3_ns_name}')
                if not checkmode:
                    print(f'\t\tcheckmode:{checkmode} do v3 ns create ...')
                    found_v3_namespace,_ = Namespace.objects.get_or_create(name=v3_ns_name)
                else:
                    continue

            # bind v3 to v1 ...
            if found_v1_namespace.namespace != found_v3_namespace:
                print(f'\tFIX - bind v3:{found_v3_namespace} to v1:{found_v1_namespace}')
                if not checkmode:
                    print(f'\t\tcheckmode:{checkmode} do v3->v1 bind ...')
                    try:
                        found_v1_namespace.namespace = found_v3_namespace
                        found_v1_namespace.save()
                    except ValueError:
                        import epdb; epdb.st()
                else:
                    continue

            current_owners = rbac.get_v3_namespace_owners(found_v3_namespace)
            if found_user not in current_owners:
                print(f'\tFIX - add {found_user} as owner of v3:{found_v3_namespace}')
                if not checkmode:
                    print(f'\t\tcheckmode:{checkmode} do owner add...')
                    rbac.add_user_to_v3_namespace(found_user, found_v3_namespace)
                else:
                    continue

            #import epdb; epdb.st()



do_check()
