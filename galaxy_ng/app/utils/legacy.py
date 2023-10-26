import logging
import re
from django.contrib.auth import get_user_model

from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.utils.galaxy import generate_unverified_email
from galaxy_ng.app.utils.namespaces import generate_v3_namespace_from_attributes
from galaxy_ng.app.utils.rbac import add_user_to_v3_namespace
from galaxy_ng.app.utils.rbac import get_v3_namespace_owners


logger = logging.getLogger(__name__)


User = get_user_model()


def sanitize_avatar_url(url):
    '''Remove all the non-url characters people have put in their avatar urls'''
    regex = (
        r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)"
        + r"(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|"
        + r"(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    )

    for match in re.findall(regex, url):
        if match and 'http' in match[0]:
            return match[0]

    return None


def process_namespace(namespace_name, namespace_info, force=False):
    '''Do all the work to sync a legacy namespace and build it's v3 counterpart'''

    logger.info(f'process legacy namespace ({namespace_info["id"]}) {namespace_name}')

    # get or create a legacy namespace with an identical name first ...
    legacy_namespace, legacy_namespace_created = \
        LegacyNamespace.objects.get_or_create(name=namespace_name)

    logger.info(f'found: {legacy_namespace} created:{legacy_namespace_created}')

    if legacy_namespace.namespace:
        logger.info(f'{legacy_namespace} has provider namespace {legacy_namespace.namespace}')
        namespace = legacy_namespace.namespace
        namespace_created = False

    else:
        logger.info(f'{legacy_namespace} does not have a provider namespace yet')

        namespace = legacy_namespace.namespace
        _owners = namespace_info['summary_fields']['owners']
        _owners = [(x.get('github_id', -1), x['username']) for x in _owners]
        _matched_owners = [x for x in _owners if x[1].lower() == namespace_name.lower()]

        if _matched_owners:
            _owner_id = _matched_owners[0][0]
            v3_namespace_name = \
                generate_v3_namespace_from_attributes(username=namespace_name, github_id=_owner_id)
        else:
            v3_namespace_name = generate_v3_namespace_from_attributes(username=namespace_name)

        logger.info(f'{legacy_namespace} creating provider namespace {v3_namespace_name}')
        namespace, namespace_created = Namespace.objects.get_or_create(name=v3_namespace_name)

    # bind legacy and v3
    if legacy_namespace.namespace != namespace:
        logger.info(f'set {legacy_namespace} provider to {namespace}')
        legacy_namespace.namespace = namespace
        legacy_namespace.save()

    changed = False

    if namespace_info['avatar_url'] and (not namespace.avatar_url or force):
        avatar_url = sanitize_avatar_url(namespace_info['avatar_url'])
        if avatar_url:
            namespace.avatar_url = avatar_url
            changed = True

    if namespace_info.get('company') and (not namespace.company or force):
        if len(namespace_info['company']) >= 60:
            namespace.company = namespace_info['company'][:60]
        else:
            namespace.company = namespace_info['company']
        changed = True

    if namespace_info.get('email') and (not namespace.email or force):
        namespace.email = namespace_info['email']
        changed = True

    if namespace_info.get('description') and (not namespace.description or force):
        if len(namespace_info['description']) >= 60:
            namespace.description = namespace_info['description'][:60]
        else:
            namespace.description = namespace_info['description']
        changed = True

    if changed:
        namespace.save()

    logger.info(f'iterating upstream owners of {legacy_namespace}')
    current_owners = get_v3_namespace_owners(namespace)
    for owner_info in namespace_info['summary_fields']['owners']:

        logger.info(f'check {legacy_namespace} owner {owner_info["username"]}')

        if owner_info.get('github_id'):
            unverified_email = generate_unverified_email(owner_info['github_id'])
        else:
            unverified_email = owner_info['username'] + '@localhost'

        owner_created = False
        owner = User.objects.filter(username=unverified_email).first()
        if not owner:
            owner = User.objects.filter(email=unverified_email).first()

        logger.info(f'found matching owner for {owner_info["username"]} = {owner}')

        # should always have an email set with default of the unverified email
        if owner and not owner.email:
            owner.email = unverified_email
            owner.save()

        if not owner:

            owner, owner_created = User.objects.get_or_create(username=owner_info['username'])

            if owner_created or not owner.email:
                # the new user should have the unverified email until they actually login
                owner.email = unverified_email
                owner.save()

        if owner not in current_owners:
            logger.info(f'adding {owner} to {namespace}')
            add_user_to_v3_namespace(owner, namespace)

    return legacy_namespace, namespace
