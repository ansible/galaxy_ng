import gzip
import json
import os

from django.contrib.auth import get_user_model

from social_django.models import UserSocialAuth

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

    # compressed for size ...
    fn = 'user_namespace_map_validated.json.gz'
    with gzip.open(fn, 'rb') as gz_file:
        raw = gz_file.read()
    umap = json.loads(raw)

    umap_by_github_id = {}
    for k,v in umap.items():
        if not v.get('github_id'):
            continue
        umap_by_github_id[v['github_id']] = v

    # verify unverified users via the email ...
    for unverified_user in User.objects.filter(email__icontains='@GALAXY.GITHUB.UNVERIFIED.COM'):
        old_guid = unverified_user.email.replace('@GALAXY.GITHUB.UNVERIFIED.COM', '')
        current_username = unverified_user.username

        # don't try to fix the unverified usernames yet ..
        if current_username.endswith('@GALAXY.GITHUB.UNVERIFIED.COM'):
            continue

        # do we know about this github id? ...
        if old_guid not in umap_by_github_id:
            continue

        gdata = umap_by_github_id[old_guid]

        # did we actually find the github user?
        if not gdata.get('github_login'):
            continue

        # casing is a pain ..
        if current_username != gdata['github_login']:
            continue

        # can't do changed logins yet ...
        if gdata['github_login_new'] and gdata['github_login_new'] != gdata['github_login']:
            continue

        # verify the user ...
        print(f'FIX - verifying {unverified_user}')
        if not checkmode:
            unverified_user.email = ''
            unverified_user.save()

    # fix the flipped users ...
    for unverified_user in User.objects.filter(username__icontains='@GALAXY.GITHUB.UNVERIFIED.COM'):
        old_guid = unverified_user.username.replace('@GALAXY.GITHUB.UNVERIFIED.COM', '')

        # do we know about this github id? ...
        if old_guid not in umap_by_github_id:
            continue

        gdata = umap_by_github_id[old_guid]

        # did we actually find the github user?
        if not gdata.get('github_login'):
            continue

        github_logins = []
        for lkey in ['github_login', 'github_login_new']:
            if gdata.get(lkey):
                github_logins.append(gdata[lkey])

        # find the new user that social auth created
        social_user = UserSocialAuth.objects.filter(uid=int(old_guid)).first()
        if not social_user:
            print('ERROR - could not find social user for guid:{old_guid} logins:{github_logins}')
            continue

        # add permissions to the new social auth user
        print(f'FIX - copy permissions from {unverified_user} to {social_user}')

        # delete the unverified user
        print(f'FIX - delete user {unverified_user}')

        #import epdb; epdb.st()



do_check()
