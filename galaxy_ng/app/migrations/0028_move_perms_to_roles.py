from django.db import migrations
from django.db.models import Count


OBJECT_PERMISSION_TRANSLATOR = [
    ((
        ("container", "change_containernamespace"),
        ("container", "namespace_push_containerdistribution"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
        ("container", "namespace_add_containerdistribution")
    ), "galaxy.execution_environment_namespace_owner"),
    ((
        ("container", "namespace_push_containerdistribution"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
    ), "galaxy.execution_environment_collaborator"),
    ((
        ("galaxy", "change_namespace"),
        ("galaxy", "upload_to_namespace"),
    ), "galaxy.namespace_owner"),
    ((
        ("galaxy", "add_synclist"),
        ("galaxy", "change_synclist"),
        ("galaxy", "delete_synclist"),
        ("galaxy", "view_synclist"),
    ), "galaxy.synclist_owner"),
]

GLOBAL_PERMISSION_TRANSLATOR = [
    ((
        ("galaxy", "change_namespace"),
        ("galaxy", "delete_namespace"),
        # ("galaxy", "view_namespace"),
        ("galaxy", "upload_to_namespace"),
        ("ansible", "delete_collection"),
        ("ansible", "change_collectionremote"),
        ("ansible", "view_collectionremote"),
        ("ansible", "modify_ansible_repo_content"),
    ), "galaxy.collection_admin"),
    ((
        ("container", "delete_containerrepository"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
        ("container", "namespace_push_containerdistribution"),
        ("container", "add_containernamespace"),
        ("container", "change_containernamespace"),
        # ("container", "namespace_add_containerdistribution")
        ("galaxy", "add_containerregistryremote"),
        ("galaxy", "change_containerregistryremote"),
        ("galaxy", "delete_containerregistryremote"),
    ), "galaxy.execution_environment_admin"),
    ((
        ("container", "change_containernamespace"),
        ("container", "namespace_push_containerdistribution"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
        ("container", "namespace_add_containerdistribution")
    ), "galaxy.execution_environment_namespace_owner"),
    ((
        ("container", "namespace_push_containerdistribution"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
    ), "galaxy.execution_environment_collaborator"),
    ((
        ("ansible", "modify_ansible_repo_content"),
    ), "galaxy.content_admin"),
    ((
        # ("galaxy", "add_namespace"),
        ("galaxy", "change_namespace"),
        # ("galaxy", "delete_namespace"),
        # ("galaxy", "view_namespace"),
        ("galaxy", "upload_to_namespace"),
        ("ansible", "delete_collection"),
    ), "galaxy.namespace_owner"),
    ((
        ("galaxy", "upload_to_namespace"),
        ("ansible", "delete_collection"),
    ), "galaxy.publisher"),
    ((
        ("galaxy", "view_group"),
        ("galaxy", "delete_group"),
        ("galaxy", "add_group"),
        ("galaxy", "change_group"),
    ), "galaxy.group_admin"),
    ((
        ("galaxy", "view_user"),
        ("galaxy", "delete_user"),
        ("galaxy", "add_user"),
        ("galaxy", "change_user"),
    ), "galaxy.user_admin"),
    ((
        ("galaxy", "add_synclist"),
        ("galaxy", "change_synclist"),
        ("galaxy", "delete_synclist"),
        ("galaxy", "view_synclist"),
    ), "galaxy.synclist_owner"),
    ((
        ("core", "change_task"),
        ("core", "delete_task"),
        ("core", "view_task"),
    ), "galaxy.task_admin"),
]

""""
MIGRATION STRATEGY:

Global Permissions:
- Apply as many locked roles as possible
- Create a new role specific to the group to apply any missing permissions

Object Group Permissions:

Objects we care about
- container namespaces
- synclists
- collection namespaces
- other?

- attempt to apply existing object roles
- create new reusable role with extra permissions

User Object Permissions:
The only places with user permissions (that we care about) are:
- container namespace owner
- tasks
"""


def batch_create(model, objects, flush=False):
    """
    Save the objects to the database in batches of 1000.
    """
    if len(objects) > 1000 or flush:
        model.objects.bulk_create(objects)
        objects.clear()


def get_roles_from_permissions(permission_iterable, translator, Role, Permission):
    """
    Translates the given set of permissions into roles based on the translator that is passed in.
    """
    roles_to_add = []

    # Use set comparisons instead of querysets to avoid unnecesary trips to the DB
    permissions = set(((p.content_type.app_label, p.codename) for p in permission_iterable))
    
    # Iterate through each locked role, apply any roles that match the group's permission
    # set and remove any permissions that are applied via roles
    for locked_perm_names, locked_rolename in translator:
        role_perms = set(locked_perm_names)

        if role_perms.issubset(permissions):
            # don't bother setting the permissions on the locked roles. They'll get applied in
            # the post migration hook.
            role, _ = Role.objects.get_or_create(name=locked_rolename, locked=True)
            roles_to_add.append(role)            
            permissions = permissions - role_perms
    
    for label, perm in permissions:
        # prefix permission roles with _permission: instead of galaxy. so that they are hidden
        # by default in the roles UI.
        role, created = Role.objects.get_or_create(
            name=f"_permission:{label}.{perm}",
            description=f"Auto generated role for permission {label}.{perm}."
        )

        if created:
            role.permissions.set([Permission.objects.get(codename=perm, content_type__app_label=label)])

        roles_to_add.append(role)

    return roles_to_add


def get_global_group_permissions(group, Role, GroupRole, Permission):
    """
    Takes in a group object and returns a list of GroupRole objects to be created for
    the given group.
    """

    group_roles = []
    perms = group.permissions.all()

    # If there are no permissions, then our job here is done
    if len(perms) == 0:
        return

    # roles, leftover_permissions = get_roles_from_permissions(perms, GLOBAL_PERMISSION_TRANSLATOR, Role)
    roles = get_roles_from_permissions(perms, GLOBAL_PERMISSION_TRANSLATOR, Role, Permission)

    # Add locked roles that match the group's permission set
    for role in roles:
        group_roles.append(GroupRole(group=group, role=role))

    # Create custom role for current Group with permissions not in Galaxy locked roles
    # if len(leftover_permissions) > 0:
    #     role, _ = Role.objects.get_or_create(
    #         name=f"galaxy._{group.name}_extra",
    #         description = f"Automatically generated. Contains extra global pmerissions for {group.name}"
    #     )
    #     for app_label, codename in leftover_permissions:
    #         role.permissions.add(group.permissions.get(codename=codename, content_type__app_label=app_label))

    #     group_roles.append(GroupRole(group=group, role=role))

    return group_roles


def get_object_group_permissions(group, Role, GroupRole, GuardianGroupObjectPermission, Permission):
    """
    Takes in a group object and returns a list of GroupRole objects to be created for
    each object that the group has permissions on.
    """
    group_roles = []
    objects_with_perms = {}

    # group the object permissions for this group by object instances to make them easier to process
    for guardian_permission in GuardianGroupObjectPermission.objects.filter(group=group):
        key = (str(guardian_permission.content_type), guardian_permission.object_pk)

        if key in objects_with_perms:
            objects_with_perms[key].append(guardian_permission)
        else:
            objects_with_perms[key] = [guardian_permission,]

    # for each object permission that this group has, map it to a role.
    for k in objects_with_perms:
        perm_list = objects_with_perms[k]
        content_type = perm_list[0].content_type
        object_id = perm_list[0].object_pk

        # TODO: Optimize container namespace and namespce roles. If user has "change_containernamespace"
        # or change_namespace give them ownership roles.

        # Add any locked roles that match the given group/objects permission set
        roles = get_roles_from_permissions(
            [p.permission for p in perm_list], OBJECT_PERMISSION_TRANSLATOR, Role, Permission)

        # Queue up the locked roles for creation
        for role in roles:
            group_roles.append(GroupRole(
                role=role,
                group=group,
                content_type=content_type,
                object_id=object_id
            ))

        # If there are remainining permissions get or create a role that matches the exact set
        # of permissions that are left over
        # if len(leftover_permissions) > 0:
        #     qs = Role.objects.annotate(
        #         perm_count = Count("permissions")).filter(perm_count=len(leftover_permissions))

        #     perms_for_new_role = []

        #     # Attempt to find an existing role with the exact set of permissions
        #     for app_label, codename in leftover_permissions:
        #         perm = Permission.objects.get(codename=codename, content_type__app_label=app_label)
        #         perms_for_new_role.append(perm)
        #         qs = qs.filter(permissions=perm)

        #     role = qs.first()

        #     # If no role is found, create a new one 
        #     if not role:
        #         perm_string = ""
        #         for p in leftover_permissions:
        #             perm_string = perm_string + "." + p.split('.', maxsplit=1)[1]
                
        #         name = f"galaxy._{content_type.model}{perm_string}"

        #         role, _ = Role.objects.get_or_create(
        #             name=name[:128],
        #             description="Auto generated role."
        #         )

        #         role.permissions.set(perms_for_new_role)

        #     group_roles.append(GroupRole(
        #         role=role,
        #         group=group,
        #         content_type=content_type,
        #         object_id=object_id
        #     ))

    return group_roles


def add_object_role_for_users_with_permission(role, permission, UserRole, GuardianUserObjectPermission):
    user_roles = []

    for guardian_permission in GuardianUserObjectPermission.objects.filter(
        permission=permission):
        user_roles.append(UserRole(
            role=role,
            user=guardian_permission.user,
            content_type=guardian_permission.content_type,
            object_id=guardian_permission.object_pk
        ))
        batch_create(UserRole, user_roles)

    # Create any remaining roles
    batch_create(UserRole, user_roles, flush=True)



def migrate_group_permissions_to_roles(apps, schema_editor):
    Group = apps.get_model("galaxy", "Group")
    GroupRole = apps.get_model("core", "GroupRole")
    UserRole = apps.get_model("core", "UserRole")
    Role = apps.get_model("core", "Role")
    Permission = apps.get_model("auth", "Permission")
    GuardianUserObjectPermission = apps.get_model("guardian", "UserObjectPermission")
    GuardianGroupObjectPermission = apps.get_model("guardian", "GroupObjectPermission")

    group_roles = []

    # Group Permissions
    for group in Group.objects.filter(name__ne="system:partner-engineers"):
        group_roles.extend(get_global_group_permissions(group, Role, GroupRole, Permission))
        group_roles.extend(get_object_group_permissions(group, Role, GroupRole, GuardianGroupObjectPermission, Permission))

        batch_create(GroupRole, group_roles)

    # Create any remaining roles
    batch_create(GroupRole, group_roles, flush=True)


def migrate_user_permissions_to_roles(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    Role = apps.get_model("core", "Role")
    UserRole = apps.get_model("core", "UserRole")
    GuardianUserObjectPermission = apps.get_model("guardian", "UserObjectPermission")

    # TODO: Migrate user permissions.
    # We only care about user permissions for container namespaces and tasks. Global permissions
    # for users are not used, and they should be ignored if they exist.

    # Get all users with change_containernamespace permissions. Change container namespace allows
    # users to set permissions on container namespaces, so it allows us to use it as a proxy for
    # users that have administrative rights on container namespace and we can just give them the
    # execution environment admin role.
    change_container_namespace = Permission.objects.get(
        codename="change_containernamespace", content_type__app_label="container")
    container_namespace_admin, _ = Role.objects.get_or_create(name="galaxy.execution_environment_namespace_owner")
    add_object_role_for_users_with_permission(
        container_namespace_admin, change_container_namespace, UserRole, GuardianUserObjectPermission)

    # When tasks are created pulp adds delete task and a few other permissions to the user that
    # initiates the task. Delete task is a good proxy for this role.
    delete_task = Permission.objects.get(
        codename="view_task", content_type__app_label="core")
    task_owner, _ = Role.objects.get_or_create(name="galaxy.task_admin")
    add_object_role_for_users_with_permission(
        task_owner, delete_task, UserRole, GuardianUserObjectPermission)


class Migration(migrations.Migration):

    dependencies = [
        ("galaxy", "0027_delete_contentredirectcontentguard"),
    ]

    operations = [
        migrations.RunPython(
            code=migrate_group_permissions_to_roles, reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            code=migrate_user_permissions_to_roles, reverse_code=migrations.RunPython.noop
        ),
    ]