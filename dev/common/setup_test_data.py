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
                GroupRole.objects.get_or_create(
                    role=Role.objects.get(name=role),
                    group=group,
                )

        return group


def _init_token(user, credentials):
    if token := credentials.get("token"):
        Token.objects.get_or_create(user=user, key=token)


for profile_name in PROFILES:
    profile = PROFILES[profile_name]
    if ldap_user := profile["username"].get("ldap"):
        print(f"Initializing ldap user for test profile: {profile_name}")
        credentials = CREDENTIALS[ldap_user]
        _init_group(credentials, profile)

    if galaxy_user := profile["username"].get("galaxy"):
        print(f"Initializing galaxy user for test profile: {profile_name}")
        u, _ = User.objects.get_or_create(username=galaxy_user)
        credentials = CREDENTIALS[galaxy_user]

        u.set_password(credentials["password"])
        u.is_superuser = profile.get("is_superuser", False)

        if group := _init_group(credentials, profile):
            u.groups.add(group)
        u.save()

        _init_token(u, credentials)


print("CollectionRemote community url points to beta-galaxy.ansible.com")
remote = CollectionRemote.objects.get(name="community")
remote.url = "https://beta-galaxy.ansible.com/api/"
remote.save()
