# import trio

# import datetime
import re
# import sys
# import time
# import django_guid
from django.contrib.auth import get_user_model

# from django.core.management.base import BaseCommand
# from pulp_ansible.app.models import AnsibleRepository
# from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES
# from pulpcore.plugin.tasking import dispatch

from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.models import Namespace
# from galaxy_ng.app.tasks.namespaces import _create_pulp_namespace
# from galaxy_ng.app.utils.galaxy import upstream_collection_iterator
# from galaxy_ng.app.utils.galaxy import upstream_namespace_iterator
# from galaxy_ng.app.utils.galaxy import upstream_role_iterator
# from galaxy_ng.app.utils.galaxy import find_namespace
from galaxy_ng.app.utils.galaxy import generate_unverified_email
from galaxy_ng.app.utils.namespaces import generate_v3_namespace_from_attributes
from galaxy_ng.app.utils.rbac import add_user_to_v3_namespace

# from pulpcore.plugin.files import PulpTemporaryUploadedFile
# from pulpcore.plugin.download import HttpDownloader
# from pulp_ansible.app.models import AnsibleNamespaceMetadata, AnsibleNamespace
# from pulpcore.plugin.tasking import add_and_remove, dispatch
# from pulpcore.plugin.models import RepositoryContent, Artifact, ContentArtifact


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


def process_namespace(namespace_name, namespace_info):
    '''Do all the work to sync a legacy namespace and build it's v3 counterpart'''

    # get or create a legacy namespace with an identical name first ...
    legacy_namespace, legacy_namespace_created = \
        LegacyNamespace.objects.get_or_create(name=namespace_name)

    if legacy_namespace.namespace:
        namespace = legacy_namespace.namespace
        namespace_created = False

    else:
        _owners = namespace_info['summary_fields']['owners']
        _owners = [(x['github_id'], x['username']) for x in _owners]
        _matched_owners = [x for x in _owners if x[1].lower() == namespace_name.lower()]

        if _matched_owners:
            _owner_id = _matched_owners[0][0]
            v3_namespace_name = \
                generate_v3_namespace_from_attributes(username=namespace_name, github_id=_owner_id)
        else:
            v3_namespace_name = generate_v3_namespace_from_attributes(username=namespace_name)

        namespace, namespace_created = Namespace.objects.get_or_create(name=v3_namespace_name)

    # bind legacy and v3
    legacy_namespace.namespace = namespace
    legacy_namespace.save()

    changed = False

    if namespace_info['avatar_url'] and not namespace.avatar_url:
        avatar_url = sanitize_avatar_url(namespace_info['avatar_url'])
        if avatar_url:
            namespace.avatar_url = avatar_url
            changed = True

    if namespace_info['company'] and not namespace.company:
        if len(namespace_info['company']) >= 60:
            namespace.company = namespace_info['company'][:60]
        else:
            namespace.company = namespace_info['company']
        changed = True

    if namespace_info['email'] and not namespace.email:
        namespace.email = namespace_info['email']
        changed = True

    if namespace_info['description'] and not namespace.description:
        if len(namespace_info['description']) >= 60:
            namespace.description = namespace_info['description'][:60]
        else:
            namespace.description = namespace_info['description']
        changed = True

    if changed:
        namespace.save()

    for owner_info in namespace_info['summary_fields']['owners']:

        unverified_email = generate_unverified_email(owner_info['github_id'])

        owner_created = False
        owner = User.objects.filter(username=unverified_email).first()
        if not owner:
            owner = User.objects.filter(email=unverified_email).first()

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

        add_user_to_v3_namespace(owner, namespace)

    return legacy_namespace, namespace
