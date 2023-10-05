from django.contrib.auth import get_user_model
from social_django.models import UserSocialAuth

from pulp_ansible.app.models import Collection
from pulp_ansible.app.models import CollectionVersion

from galaxy_ng.app.utils import rbac
from galaxy_ng.app.utils.galaxy import generate_unverified_email
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.models import Namespace


User = get_user_model()


def transform_name(github_login):
    ns = github_login.lower().replace('-', '_')
    if ns[0].isdigit():
        ns = 'gh_' + ns
    return ns


def find_related_v3_namespaces(github_login):
    transformed = github_login.lower().replace('-', '_')
    #if transformed[0].isdigit():
    #    transformed = 'gh_' + transformed

    namespaces = Namespace.objects.filter(name__icontains=transformed)
    return namespaces


for social_user in UserSocialAuth.objects.all().order_by('id'):
    sid = social_user.id
    current_user = social_user.user
    current_username = current_user.username
    current_email = current_user.email
    github_login = social_user.extra_data.get('login')
    github_id = social_user.extra_data.get('id')
    transformed_login = transform_name(github_login)

    unverified_email = generate_unverified_email(github_id)

    #if current_username == github_login:
    #    continue

    galaxy_user_by_login = User.objects.filter(username=github_login).first()
    galaxy_user_by_unverified_email = User.objects.filter(username=unverified_email).first()
    galaxy_user_by_unverified_name = User.objects.filter(email=unverified_email).first()

    if not galaxy_user_by_unverified_email and not galaxy_user_by_unverified_name:
        continue

    synced_users = []
    if galaxy_user_by_unverified_email and galaxy_user_by_unverified_name:
        if galaxy_user_by_unverified_email.id == galaxy_user_by_unverified_name.id:
            galaxy_user_by_unverified_name = None
        if galaxy_user_by_unverified_email:
            synced_users.append(galaxy_user_by_unverified_email)
        if galaxy_user_by_unverified_name:
            synced_users.append(galaxy_user_by_unverified_name)

    # this person got the right user association?
    synced_users = [x for x in synced_users if x.id != current_user.id]
    if current_user.email != unverified_email and not synced_users:
        continue

    print(f'{sid}. {github_id}|{github_login} current:{current_username} current_email:{current_email}')

    for synced_user in synced_users:
        print(f'\tsynced_user: {synced_user.id}')
        print(f'\t\t{synced_user}')
        print(f'\t\t\tusername:{synced_user.username}')
        print(f'\t\t\temail:{synced_user.email}')

    if len(synced_users) > 1:
        raise Exception('too many synced users found')

    if not synced_users and current_user.email and current_user.email == unverified_email:
        print(f'\t FIX - set email to empty string')
        current_user.email = ''
        current_user.save()
        continue

    # proably shouldn't be here if no sync users found?
    if not synced_users:
        continue
    synced_user = synced_users[0]

    # copy ownership ...
    owned_namespaces = rbac.get_owned_v3_namespaces(synced_user)
    print(f'\t{synced_user.id} owns {owned_namespaces}')
    if owned_namespaces:
        for ns in owned_namespaces:
            ns_owners = rbac.get_v3_namespace_owners(ns)
            print(f'\t{ns} owners ...')
            for xowner in ns_owners:
                print(f'\t\t{xowner}')
            if current_user not in ns_owners:
                print(f'\tFIX - make {current_user} owner of {ns}')
                rbac.add_user_to_v3_namespace(current_user, ns)

    if synced_user != current_user and \
            (synced_user.username == unverified_email or synced_user.email == unverified_email):
        print(f'\tFIX - delete the sync user {synced_user}')
        synced_user.delete()

    related_namespaces = find_related_v3_namespaces(github_login)
    for rnamespace in related_namespaces:
        print(f'\trelated: {rnamespace}')

    # legacy namespaces ... ?
    provider_namespace = None
    legacy_namespace = LegacyNamespace.objects.filter(name=github_login).first()
    print(f'\tlegacy_namespace:{legacy_namespace}')
    if legacy_namespace:
        provider_namespace = legacy_namespace.namespace
        if provider_namespace:
            print(f'\t\tprovider:{provider_namespace}')

    if legacy_namespace and provider_namespace and \
        legacy_namespace.name == provider_namespace.name and \
        provider_namespace in owned_namespaces:
            continue

    if legacy_namespace and provider_namespace and \
        transformed_login == provider_namespace.name and \
        provider_namespace in owned_namespaces:
            continue

    correct_namespace = Namespace.objects.filter(name=transformed_login).first()

    if provider_namespace.name == transformed_login + '0':
        print(f'\t\tFIX - set v1:{legacy_namespace} provider namespace to {correct_namespace}')
        legacy_namespace.namespace = correct_namespace
        legacy_namespace.save()

        # has content?
        col_count = Collection.objects.filter(namespace=provider_namespace.name).count()
        cv_count = CollectionVersion.objects.filter(namespace=provider_namespace.name).count()
        role_count = LegacyRole.objects.filter(namespace__name=provider_namespace.name).count()

        if (col_count + cv_count + role_count) == 0:
            print(f'\t\tFIX - delete v3:{provider_namespace}')
            provider_namespace.delete()

    #print(f'\tFIX - delete the sync user {synced_user}')
    #synced_user.delete()
