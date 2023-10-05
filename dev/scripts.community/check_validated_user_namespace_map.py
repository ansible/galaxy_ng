import gzip
import json
import os

from django.contrib.auth import get_user_model

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace


User = get_user_model()


def do_check():

    checkmode = True
    if os.environ.get('CHECK_MODE') == "0":
        checkmode = False

    fn = 'user_namespace_map_validated.json.gz'
    with gzip.open(fn, 'rb') as gz_file:
        raw = gz_file.read()
    umap = json.loads(raw)

    uids = list(umap.keys())
    uids = sorted(uids, key=lambda x: int(x))
    for uid in uids:
        print(uid)

        old_data = umap[uid]
        if not old_data.get('github_login_verified'):
            continue

        galaxy_username = old_data['galaxy_username']
        github_login = old_data['github_login']
        if old_data['github_login_new']:
            github_login = old_data['github_login_new']

        # worry about this later ...
        if galaxy_username != github_login:
            continue

        found_user = User.objects.filter(username=galaxy_username).first()
        if not found_user:
            print(f'\tFIX - create user {galaxy_username}')
            if not checkmode:
                print(f'\t\tcheckmode:{checkmode} do user create ...')
                found_user, _ = User.objects.get_or_create(username=galaxy_username)

        #import epdb; epdb.st()



do_check()
