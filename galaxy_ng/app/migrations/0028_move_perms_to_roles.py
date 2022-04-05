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


def batch_process(model, objects, flush=False):
    if len(objects) > 1000 or flush:
        # print(f'#{model.__name__} = {len(objects)}')
        model.objects.bulk_create(objects)
        objects.clear()


def filter_against_galaxy_locked_roles(
    apps, permissions, perms_to_remove, group=None, user=None, group_roles=None, user_roles=None
):
    GroupRole = apps.get_model("core", "GroupRole")
    UserRole = apps.get_model("core", "UserRole")
    Permission = apps.get_model("auth", "Permission")
    Role = apps.get_model("core", "Role")
    # Use Galaxy locked Roles where possible
    for locked_perm_names, locked_rolename in MODEL_PERMISSION_TRANSLATOR:

        # for app_label, codename in locked_perm_names:
        #    print(f'app_label: {app_label}')
        #    print(f'codename: {codename}')

        locked_perms = [Permission.objects.filter(
            content_type__app_label=app_label, codename=codename
        ).first() for app_label, codename in locked_perm_names]
        print(f'\tlocked_rolename:{locked_rolename} locked_perms:{len(locked_perms)}:{locked_perms}')

        if all(locked_perms):
            # compare locked role perms to perms
            if all((locked_perm in permissions for locked_perm in locked_perms)):
                # add current locked_role to list to add to current group
                locked_role, locked_role_created = Role.objects.get_or_create(
                    name=locked_rolename,
                    defaults={"locked": True}
                )
                print(f'Locked role:{locked_role} created:{locked_role_created}')
                if locked_role_created:
                    for locked_perm in locked_perms:
                        locked_role.permissions.add(locked_perm)
                if group is not None and group_roles is not None:
                    if len(GroupRole.objects.filter(group=group, role=locked_role)) == 0:
                        group_roles.append(GroupRole(group=group, role=locked_role))
                if user is not None and user_roles is not None:
                    if len(UserRole.objects.filter(user=user, role=locked_role)) == 0:
                        user_roles.append(UserRole(user=user, role=locked_role))

                # add permissions from locked_perms to list to be removed
                perms_to_remove.extend(locked_perms)

            # Handle batches
            if group is not None and group_roles is not None:
                batch_process(GroupRole, group_roles)
            if user is not None and user_roles is not None:
                batch_process(UserRole, user_roles)

        # if group_roles is not None:
        #     print(f'\tgroup_roles count: {len(group_roles)}')
        # if user_roles is not None:
        #     print(f'\tuser_roles count: {len(user_roles)}')
        # print(f'\tperms_to_remove count: {len(perms_to_remove)}')


def remove_locked_perms_from_permissions(perms_to_remove, permissions):
    # permissions_to_remove: list of Permission objects to remove
    # permissions: queryset of Permission objects
    for p in perms_to_remove:
        permissions = permissions.exclude(id=p.id)
    perms_to_remove.clear()
    return permissions


def move_permissions_to_roles(apps, schema_editor):
    Group = apps.get_model("galaxy", "Group")
    GroupRole = apps.get_model("core", "GroupRole")
    UserRole = apps.get_model("core", "UserRole")
    Role = apps.get_model("core", "Role")
    UserObjectPermission = apps.get_model("guardian", "UserObjectPermission")
    GroupObjectPermission = apps.get_model("guardian", "GroupObjectPermission")

    group_roles = []
    user_roles = []

    # Model Permissions
    for group in Group.objects.filter(name__ne="system:partner-engineers"):

        print(f'process group:{group}')

        permissions = group.permissions.all()
        perms_to_remove = []

        # Use Galaxy locked Roles where possible
        filter_against_galaxy_locked_roles(
            apps, permissions, perms_to_remove, group=group, group_roles=group_roles
        )

        # remove permissions covered by locked_roles from the groups permission list
        permissions = remove_locked_perms_from_permissions(perms_to_remove, permissions)

        # Create custom role for current Group with permissions not in Galaxy locked roles
        if len(permissions) > 0:
            print(f'\tCREATE {group.name}_role ...')
            role, _ = Role.objects.get_or_create(name=f"galaxy.{group.name}_role")
            role.permissions.set(permissions)
            group_roles.append(GroupRole(group=group, role=role))

    # Group Object Permissions
    groups = {}
    for gop in GroupObjectPermission.objects.all():
        perms_to_remove = []

        print(f'process gop {gop}')

        current_group_object_pk = f"{gop.group.name}_{gop.object_pk}"
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

        print(f'process[2] group {g}')

        group = groups[g]['group']
        permissions = groups[g]['permissions']
        perms_to_remove = []
        rolename = f"galaxy.{groups[g]['group'].name}_{groups[g]['object_pk']}"
        role, _ = Role.objects.get_or_create(name=rolename)

        # Use Galaxy locked Roles where possible
        filter_against_galaxy_locked_roles(
            apps, permissions, perms_to_remove, group=group, group_roles=group_roles
        )

        # remove permissions covered by locked_roles from the groups permission list
        permissions = remove_locked_perms_from_permissions(perms_to_remove, permissions)

        for perm in permissions:
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
        batch_process(GroupRole, group_roles)

    # User Object Permissions
    users = {}
    for uop in UserObjectPermission.objects.all():

        print(f'process uop {uop}')

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

        print(f'process user {u}')

        user = users[u]['user']
        permissions = users[u]['permissions']
        perms_to_remove = []
        rolename = f"galaxy.{users[u]['user'].username}_{users[u]['object_pk']}"
        role, _ = Role.objects.get_or_create(name=rolename)

        # Use Galaxy locked Roles where possible
        filter_against_galaxy_locked_roles(
            apps, permissions, perms_to_remove, user=user, user_roles=user_roles
        )

        # remove permissions covered by locked_roles from the groups permission list
        permissions = remove_locked_perms_from_permissions(perms_to_remove, permissions)

        for perm in permissions:
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
        batch_process(UserRole, user_roles)

    # Process any Group/UserRoles not handled in batches
    batch_process(GroupRole, group_roles, flush=True)
    batch_process(UserRole, user_roles, flush=True)

    # Remove direct Group Permissions
    for group in Group.objects.filter(name__ne="system:partner-engineers"):
        print(f'{group} clear permissions')
        group.permissions.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("galaxy", "0027_delete_contentredirectcontentguard"),
    ]

    operations = [
        migrations.RunPython(
            code=move_permissions_to_roles, reverse_code=migrations.RunPython.noop
        ),
    ]