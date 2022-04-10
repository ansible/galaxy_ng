from django.db import migrations


MODEL_PERMISSION_TRANSLATOR = [
    ((
        ("galaxy", "change_namespace"),
        ("galaxy", "delete_namespace"),
        ("galaxy", "view_namespace"),
        ("galaxy", "upload_to_namespace"),
        ("ansible", "delete_collection"),
    ), "galaxy.collection_admin"),
    ((
        ("container", "delete_containerrepository"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
        ("container", "namespace_push_containerdistribution"),
        ("container", "add_containernamespace"),
        ("container", "change_containernamespace"),
    ), "galaxy.execution_environment_admin"),
    ((
        ("ansible", "modify_ansible_repo_content"),
    ), "galaxy.content_admin"),
    ((
        ("galaxy", "add_namespace"),
        ("galaxy", "change_namespace"),
        ("galaxy", "delete_namespace"),
        ("galaxy", "view_namespace"),
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
        ("ansible", "change_collectionremote"),
    ), "galaxy.synclist_owner"),
]


def remove_locked_perms_from_permissions(perms_to_remove, permissions):
    # permissions_to_remove: list of Permission objects to remove
    # permissions: queryset of Permission objects
    for p in perms_to_remove:
        permissions = permissions.exclude(id=p.id)
    return permissions


def move_permissions_to_roles(apps, schema_editor):
    Group = apps.get_model("galaxy", "Group")
    GroupRole = apps.get_model("core", "GroupRole")
    UserRole = apps.get_model("core", "UserRole")
    Permission = apps.get_model("auth", "Permission")
    Role = apps.get_model("core", "Role")
    UserObjectPermission = apps.get_model("guardian", "UserObjectPermission")
    GroupObjectPermission = apps.get_model("guardian", "GroupObjectPermission")

    group_roles = []
    user_roles = []

    # Model Permissions
    for group in Group.objects.filter(name__ne="system:partner-engineers"):
        permissions = group.permissions.all()
        perms_to_remove = []

        # Use Galaxy locked Roles where possible
        for locked_perm_names, locked_rolename in MODEL_PERMISSION_TRANSLATOR:
            locked_perms = [Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            ).first() for app_label, codename in locked_perm_names]

            if all(locked_perms):
                # compare locked role perms to perms
                if all((locked_perm in permissions for locked_perm in locked_perms)):
                    # add current locked_role to list to add to current group
                    locked_role, _ = Role.objects.get_or_create(
                        name=locked_rolename,
                        defaults={"locked": True}
                    )
                    group_roles.append(GroupRole(group=group, role=locked_role))

                    # add permissions from locked_perms to list to be removed
                    perms_to_remove.extend(locked_perms)

            # Handle batches
            if len(group_roles) > 1000:
                GroupRole.objects.bulk_create(group_roles)
                group_roles.clear()

        # remove permissions covered by locked_roles from the groups permission list
        permissions = remove_locked_perms_from_permissions(perms_to_remove, permissions)

        # Create custom role for current Group with permissions not in Galaxy locked roles
        if len(permissions) > 0:
            role, _ = Role.objects.get_or_create(name=f"{group.name}_role")
            role.permissions.set(permissions)
            group_roles.append(GroupRole(group=group, role=role))

    # Group Object Permissions
    groups = {}
    for gop in GroupObjectPermission.objects.all():
        current_group_object_pk =f"{gop.group.name}_{gop.object_pk}"
        if current_group_object_pk not in groups:
            groups[current_group_object_pk] = {
                "group": gop.group,
                "content_type": gop.content_type,
                "object_pk": gop.object_pk,
                "permissions": [gop.permission],
            }
        else:
            groups[current_group_object_pk]["permissions"].append(gop.permission)

    for g in groups:
        rolename = f"{groups[g]['group'].name}_{groups[g]['object_pk']}"
        role, _ = Role.objects.get_or_create(name=rolename)
        for perm in groups[g]['permissions']:
            role.permissions.add(perm)
        group_role = GroupRole(
            group=groups[g]['group'],
            role=role,
            content_type=groups[g]['content_type'],
            object_id=groups[g]['object_pk'],
        )

        if (group_role not in GroupRole.objects.all()):
            group_roles.append(group_role)

        # Handle batches
        if len(group_roles) > 1000:
            GroupRole.objects.bulk_create(group_roles)
            group_roles.clear()

    # User Object Permissions
    users = {}
    for uop in UserObjectPermission.objects.all():
        current_user_object_pk = f"{uop.user.username}_{uop.object_pk}"
        if current_user_object_pk not in users:
            users[current_user_object_pk] = {
                "user": uop.user,
                "content_type": uop.content_type,
                "object_pk": uop.object_pk,
                "permissions": [uop.permission],
            }
        else:
            users[current_user_object_pk]["permissions"].append(uop.permission)

    for u in users:
        rolename = f"{users[u]['user'].username}_{users[u]['object_pk']}"
        role, _ = Role.objects.get_or_create(name=rolename)
        for perm in users[u]['permissions']:
            role.permissions.add(perm)
        user_role = UserRole(
            user=users[u]['user'],
            role=role,
            content_type=users[u]['content_type'],
            object_id=users[u]['object_pk'],
        )

        if (user_role not in UserRole.objects.all()):
            user_roles.append(user_role)

        # Handle batches
        if len(user_roles) > 1000:
            UserRole.objects.bulk_create(user_roles)
            user_roles.clear()

    # Process any not handled in batches
    GroupRole.objects.bulk_create(group_roles)
    group_roles.clear()
    UserRole.objects.bulk_create(user_roles)
    user_roles.clear()

    # Remove direct Group Permissions
    for group in Group.objects.filter(name__ne="system:partner-engineers"):
        group.permissions.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("galaxy", "0025_add_content_guard_to_distributions"),
        ("core", "0081_reapplabel_group_permissions"),
    ]

    operations = [
        migrations.RunPython(
            code=move_permissions_to_roles, reverse_code=migrations.RunPython.noop
        ),
    ]
