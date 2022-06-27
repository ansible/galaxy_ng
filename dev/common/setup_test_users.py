from guardian.shortcuts import assign_perm
from rest_framework.authtoken.models import Token

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models.auth import Group, User

# TODO: remove fixuser.py, create_objects.py, jdoe_pe_group.py (if ahub calls this script)
# TODO: see if can remove create_token.py and create_admin_token.py see what calls them

print("Add a group that has namespace permissions")
test_group, _ = Group.objects.get_or_create(name="ns_group_for_tests")


print("Add partner-engineers group")
# TODO: remove when we run mgmt command maintain-pe-group on every crc deploy after roles rbac
PE_GROUP_NAME = "system:partner-engineers"
pe_group, _ = Group.objects.get_or_create(name=PE_GROUP_NAME)
pe_perms = [
    # groups
    "galaxy.view_group",
    "galaxy.delete_group",
    "galaxy.add_group",
    "galaxy.change_group",
    # users
    "galaxy.view_user",
    "galaxy.delete_user",
    "galaxy.add_user",
    "galaxy.change_user",
    # collections
    "ansible.modify_ansible_repo_content",
    "ansible.delete_collection",
    # namespaces
    "galaxy.add_namespace",
    "galaxy.change_namespace",
    "galaxy.upload_to_namespace",
    "galaxy.delete_namespace",
]
for perm in pe_perms:
    assign_perm(perm, pe_group)


print("Get or create test users to match keycloak passwords")
basic_user, _ = User.objects.get_or_create(username="iqe_normal_user")
basic_user.set_password("redhat")
basic_user.groups.add(test_group)
basic_user.save()

partner_engineer, _ = User.objects.get_or_create(username="jdoe")
partner_engineer.set_password("redhat")
partner_engineer.groups.add(test_group)
partner_engineer.groups.add(pe_group)
partner_engineer.save()

org_admin, _ = User.objects.get_or_create(username="org-admin")
org_admin.set_password("redhat")
org_admin.groups.add(test_group)
org_admin.save()

admin, _ = User.objects.get_or_create(username="notifications_admin")
admin.set_password("redhat")
admin.is_superuser = True
admin.is_staff = True
admin.save()


print("Get or create tokens for test users")
Token.objects.get_or_create(user=basic_user, key="abcdefghijklmnopqrstuvwxyz1234567891")
Token.objects.get_or_create(user=partner_engineer, key="abcdefghijklmnopqrstuvwxyz1234567892")
Token.objects.get_or_create(user=org_admin, key="abcdefghijklmnopqrstuvwxyz1234567893")
Token.objects.get_or_create(user=admin, key="abcdefghijklmnopqrstuvwxyz1234567894")


print("Get or create namespaces + add object permissions to group")
# TODO: after roles rbac, add object permissions to new role, then add role to group
for nsname in ["autohubtest2", "autohubtest3"]:
    ns, _ = Namespace.objects.get_or_create(name=nsname)
    assign_perm("change_namespace", test_group, ns)
    assign_perm("upload_to_namespace", test_group, ns)
