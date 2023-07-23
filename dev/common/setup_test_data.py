import os

from django.contrib.contenttypes.models import ContentType
from pulpcore.plugin.models.role import GroupRole, Role
from pulp_ansible.app.models import CollectionRemote
from rest_framework.authtoken.models import Token

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models.auth import Group, User

from galaxy_ng.tests.integration.constants import CREDENTIALS, PROFILES


"""
Setup test data used in integration tests.
"""

TEST_NAMESPACES = {}

auth_backend = os.environ.get('HUB_TEST_AUTHENTICATION_BACKEND')

print("Create test namespaces")
for nsname in ["autohubtest2", "autohubtest3", "signing"]:
    ns, _ = Namespace.objects.get_or_create(name=nsname)
    TEST_NAMESPACES[nsname] = ns


def _init_group(credentials, profile):
    if g := credentials.get("group"):
        group, _ = Group.objects.get_or_create(name=g)

        # add namespace ownership to the group
        if namespaces := profile.get("namespaces"):
            for ns in namespaces:
                ns = TEST_NAMESPACES[ns]

                # assign_role creates duplicate entries, so we'll use this directly.
                GroupRole.objects.get_or_create(
                    role=Role.objects.get(name="galaxy.collection_namespace_owner"),
                    group=group,
                    content_type=ContentType.objects.get(model="namespace"),
                    object_id=ns.id,
                )

        if roles := profile.get("roles"):
            for role in roles:

                group_roles = GroupRole.objects.filter(
                    role=Role.objects.get(name=role),
                    group=group,
                )

                if group_roles.exists() is False:
                    GroupRole.objects.create(
                        role=Role.objects.get(name=role),
                        group=group,
                    )

        return group


def _init_token(user, credentials):
    if token := credentials.get("token"):
        Token.objects.get_or_create(user=user, key=token)


def _init_user(user_profile, profile, profile_name):
    username = profile["username"]
    if galaxy_user := username.get(user_profile):
        print(f"Initializing {user_profile} user for test profile: {profile_name}")
        u, _ = User.objects.get_or_create(username=galaxy_user)
        credentials = CREDENTIALS[galaxy_user]

        u.set_password(credentials["password"])
        u.is_superuser = profile.get("is_superuser", False)

        if group := _init_group(credentials, profile):
            u.groups.add(group)
        u.save()

        _init_token(u, credentials)


for profile_name in PROFILES:
    profile = PROFILES[profile_name]
    try:
        if profile['username'] is None:
            continue

        if ldap_user := profile["username"].get("ldap"):
            print(f"Initializing ldap user for test profile: {profile_name}")
            credentials = CREDENTIALS[ldap_user]
            _init_group(credentials, profile)

        _init_user("galaxy", profile, profile_name)

        # create additional community (github) users
        if auth_backend == "community":
            _init_user("community", profile, profile_name)
    except Exception as e:
        print(e)

print("CollectionRemote community url points to beta-galaxy.ansible.com")
remote = CollectionRemote.objects.get(name="community")
remote.url = "https://beta-galaxy.ansible.com/api/"
remote.save()
