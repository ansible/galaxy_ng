from galaxy_ng.app.models.auth import Group, User
from guardian.shortcuts import assign_perm

# FIXME(awcrosby): refactor this module when integration tests don't use admin user
# and we are running mgmt command maintain-pe-group on every crc deploy after rbac

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

user = User.objects.create_user('jdoe', password='bar')
user.groups.add(pe_group)
user.save()
