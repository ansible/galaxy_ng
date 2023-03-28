from django.contrib.contenttypes.models import ContentType
from pulpcore.plugin.models.role import GroupRole, Role
from pulpcore.plugin.util import assign_role
from rest_framework.authtoken.models import Token

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models.auth import Group, User

"""
Setup test data used in integration tests.
"""

print("Add a group that has namespace permissions")
test_group, _ = Group.objects.get_or_create(name="ns_group_for_tests")

print("Ensure partner-engineers group created and has roles assigned")
PE_GROUP_NAME = "system:partner-engineers"
pe_group, _ = Group.objects.get_or_create(name=PE_GROUP_NAME)
pe_roles = [
    "galaxy.group_admin",
    "galaxy.user_admin",
    "galaxy.collection_admin",
]
roles_in_group = [group_role.role.name for group_role in pe_group.object_roles.all()]
for role in pe_roles:
    if role not in roles_in_group:
        assign_role(rolename=role, entity=pe_group)

print("Add a group that has registry and registry remote roles assigned")
ee_group, _ = Group.objects.get_or_create(name="ee_group_for_tests")
ee_role = 'galaxy.execution_environment_admin'
roles_in_ee_group = [group_role.role.name for group_role in ee_group.object_roles.all()]
if ee_role not in roles_in_ee_group:
    assign_role(rolename=ee_role, entity=ee_group)

print("Get or create test users to match keycloak passwords")

# in ephemeral keycloak this user is part of customer account: 6089723
basic_user, _ = User.objects.get_or_create(username="iqe_normal_user")
basic_user.set_password("redhat")
basic_user.groups.add(test_group)
basic_user.save()

# in ephemeral keycloak this user is part of customer account: 6089719
partner_engineer, _ = User.objects.get_or_create(username="jdoe")
partner_engineer.set_password("redhat")
partner_engineer.groups.add(test_group)
partner_engineer.groups.add(pe_group)
partner_engineer.save()

# in ephemeral keycloak this user is part of customer account: 6089720
org_admin, _ = User.objects.get_or_create(username="org-admin")
org_admin.set_password("redhat")
org_admin.groups.add(test_group)
org_admin.save()

# in ephemeral keycloak this user is part of customer account: 6089726
admin, _ = User.objects.get_or_create(username="notifications_admin")
admin.set_password("redhat")
admin.is_superuser = True
admin.is_staff = True
admin.save()

# in ephemeral keycloak this user is part of customer account: 6089726
iqe_admin, _ = User.objects.get_or_create(username="iqe_admin")
iqe_admin.set_password("redhat")
iqe_admin.is_superuser = True
iqe_admin.is_staff = True
iqe_admin.save()

# Note: this user is not a part of ephemeral keycloak users
ee_admin, _ = User.objects.get_or_create(username="ee_admin")
ee_admin.set_password("redhat")
ee_admin.groups.add(ee_group)
ee_admin.save()

# Note: User not used for integration tests, not part of ephemeral keycloak users
legacy_admin, _ = User.objects.get_or_create(username="admin")
legacy_admin.set_password("admin")
legacy_admin.email = "admin@example.com"
legacy_admin.is_superuser = True
legacy_admin.is_staff = True
legacy_admin.save()


print("Get or create tokens for test users")
Token.objects.get_or_create(user=basic_user, key="abcdefghijklmnopqrstuvwxyz1234567891")
Token.objects.get_or_create(user=partner_engineer, key="abcdefghijklmnopqrstuvwxyz1234567892")
Token.objects.get_or_create(user=org_admin, key="abcdefghijklmnopqrstuvwxyz1234567893")
Token.objects.get_or_create(user=admin, key="abcdefghijklmnopqrstuvwxyz1234567894")
Token.objects.get_or_create(user=ee_admin, key="abcdefghijklmnopqrstuvwxyz1234567895")


print("Get or create namespaces + add object permissions to group")
for nsname in ["autohubtest2", "autohubtest3"]:
    ns, _ = Namespace.objects.get_or_create(name=nsname)
    # connect group to role for this namespace object
    GroupRole.objects.get_or_create(
        role=Role.objects.get(name="galaxy.collection_namespace_owner"),
        group=test_group,
        content_type=ContentType.objects.get(model="namespace"),
        object_id=ns.id,
    )

print("Create a signing namespace and roles")
signing_ns, _ = Namespace.objects.get_or_create(name="signing")
# connect group to role for this namespace object
GroupRole.objects.get_or_create(
    role=Role.objects.get(name="galaxy.collection_namespace_owner"),
    group=pe_group,
    content_type=ContentType.objects.get(model="namespace"),
    object_id=signing_ns.id,
)

print("Add a group that exists in the testing LDAP container")
ldap_group, _ = Group.objects.get_or_create(name="admin_staff")
