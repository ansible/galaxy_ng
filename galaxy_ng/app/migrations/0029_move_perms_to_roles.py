from django.db import migrations, connection
from django.conf import settings


OBJECT_PERMISSION_TRANSLATOR = [
    ((
        ("container", "change_containernamespace"),
        ("container", "namespace_push_containerdistribution"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
        ("container", "namespace_add_containerdistribution"),
    ), "galaxy.execution_environment_namespace_owner"),
    ((
        ("container", "namespace_push_containerdistribution"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
    ), "galaxy.execution_environment_collaborator"),
    ((
        ("galaxy", "change_namespace"),
        ("galaxy", "upload_to_namespace"),
    ), "galaxy.collection_namespace_owner"),
    ((
        ("galaxy", "add_synclist"),
        ("galaxy", "change_synclist"),
        ("galaxy", "delete_synclist"),
        ("galaxy", "view_synclist"),
    ), "galaxy.synclist_owner"),
]

GLOBAL_PERMISSION_TRANSLATOR = [
    ((
        ("galaxy", "add_namespace"),
        ("galaxy", "change_namespace"),
        ("galaxy", "delete_namespace"),
        ("galaxy", "upload_to_namespace"),
        ("ansible", "delete_collection"),
        ("ansible", "change_collectionremote"),
        ("ansible", "view_collectionremote"),
        ("ansible", "modify_ansible_repo_content"),
        ("container", "delete_containerrepository"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
        ("container", "namespace_push_containerdistribution"),
        ("container", "add_containernamespace"),
        ("container", "change_containernamespace"),
        # ("container", "namespace_add_containerdistribution"),
        ("galaxy", "add_containerregistryremote"),
        ("galaxy", "change_containerregistryremote"),
        ("galaxy", "delete_containerregistryremote"),
    ), "galaxy.content_admin"),

    # COLLECTIONS
    ((
        ("galaxy", "add_namespace"),
        ("galaxy", "change_namespace"),
        ("galaxy", "delete_namespace"),
        ("galaxy", "upload_to_namespace"),
        ("ansible", "delete_collection"),
        ("ansible", "change_collectionremote"),
        ("ansible", "view_collectionremote"),
        ("ansible", "modify_ansible_repo_content"),
    ), "galaxy.collection_admin"),
    ((
        ("galaxy", "add_namespace"),
        ("galaxy", "change_namespace"),
        ("galaxy", "upload_to_namespace"),
    ), "galaxy.collection_publisher"),
    ((
        ("ansible", "change_collectionremote"),
        ("ansible", "view_collectionremote"),
        ("ansible", "modify_ansible_repo_content"),
    ), "galaxy.collection_curator"),
    ((
        ("galaxy", "change_namespace"),
        ("galaxy", "upload_to_namespace"),
    ), "galaxy.collection_namespace_owner"),

    # EXECUTION ENVIRONMENTS
    ((
        ("container", "delete_containerrepository"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
        ("container", "namespace_push_containerdistribution"),
        ("container", "add_containernamespace"),
        ("container", "change_containernamespace"),
        # Excluding this because it's only used for object assignment, not model
        # ("container", "namespace_add_containerdistribution"),
        ("galaxy", "add_containerregistryremote"),
        ("galaxy", "change_containerregistryremote"),
        ("galaxy", "delete_containerregistryremote"),
    ), "galaxy.execution_environment_admin"),
    ((
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
        ("container", "namespace_push_containerdistribution"),
        ("container", "add_containernamespace"),
        ("container", "change_containernamespace"),
        # ("container", "namespace_add_containerdistribution"),
    ), "galaxy.execution_environment_publisher"),
    ((
        ("container", "change_containernamespace"),
        ("container", "namespace_push_containerdistribution"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
        # ("container", "namespace_add_containerdistribution"),
    ), "galaxy.execution_environment_namespace_owner"),
    ((
        ("container", "namespace_push_containerdistribution"),
        ("container", "namespace_change_containerdistribution"),
        ("container", "namespace_modify_content_containerpushrepository"),
    ), "galaxy.execution_environment_collaborator"),

    # ADMIN STUFF
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


def batch_create(model, objects, flush=False):
    """
    Save the objects to the database in batches of 1000.
    """
    if len(objects) > 1000 or flush:
        model.objects.bulk_create(objects)
        objects.clear()


def get_roles_from_permissions(permission_iterable, translator, Role, Permission, super_permissions=None):
    """
    Translates the given set of permissions into roles based on the translator that is passed in.
    """
    roles_to_add = []
    if super_permissions is None:
        super_permissions = {}

    # Use set comparisons instead of querysets to avoid unnecesary trips to the DB
    permissions = set(((p.content_type.app_label, p.codename) for p in permission_iterable))
    
    # Iterate through each locked role, apply any roles that match the group's permission
    # set and remove any permissions that are applied via roles
    for locked_perm_names, locked_rolename in translator:
        role_perms = set(locked_perm_names)

        super_perm_for_role = super_permissions.get(locked_rolename, None)

        # Some objects have permissions that allow users to change permissions on the object.
        # An example of this is galaxy.change_namespace allows the user to change their own
        # permissions on the namespace effectively giving them all the permissions. If the
        # user has one of these permissions, just give them the full role for the object.
        if role_perms.issubset(permissions) or super_perm_for_role in permissions:
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
        return group_roles

    roles = get_roles_from_permissions(perms, GLOBAL_PERMISSION_TRANSLATOR, Role, Permission)

    # Add locked roles that match the group's permission set
    for role in roles:
        group_roles.append(GroupRole(group=group, role=role))
    
    return group_roles


def get_object_group_permissions(group, Role, GroupRole, ContentType, Permission):
    """
    Takes in a group object and returns a list of GroupRole objects to be created for
    each object that the group has permissions on.
    """
    group_roles = []
    objects_with_perms = {}

    # Use raw sql because guardian won't be available
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT object_pk, content_type_id, permission_id FROM"
            f" guardian_groupobjectpermission WHERE group_id={group.pk};"
        )

        # group the object permissions for this group by object instances to make them easier to process
        for object_pk, content_id, permission_id in cursor.fetchall():
            key = (content_id, object_pk)

            if key in objects_with_perms:
                objects_with_perms[key].append(permission_id)
            else:
                objects_with_perms[key] = [permission_id,]
    
    # for each object permission that this group has, map it to a role.
    for k in objects_with_perms:
        perm_list = objects_with_perms[k]
        content_type_id = k[0]
        object_id = k[1]

        content_type = ContentType.objects.get(pk=content_type_id)

        permissions = Permission.objects.filter(pk__in=perm_list)

        # Add any locked roles that match the given group/objects permission set
        roles = get_roles_from_permissions(
            permissions,
            OBJECT_PERMISSION_TRANSLATOR,
            Role,
            Permission,
            super_permissions={
                "galaxy.execution_environment_namespace_owner":
                    ("container", "change_containernamespace"),
                "galaxy.collection_namespace_owner": ("galaxy", "change_namespace"),
            }
        )

        # Queue up the locked roles for creation
        for role in roles:
            group_roles.append(GroupRole(
                role=role,
                group=group,
                content_type=content_type,
                object_id=object_id
            ))

    return group_roles


def add_object_role_for_users_with_permission(role, permission, UserRole, ContentType, User):
    user_roles = []

    # Use raw sql because guardian won't be available
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT object_pk, content_type_id, user_id FROM"
            f" guardian_userobjectpermission WHERE permission_id={permission.pk};"
        )

        for object_pk, content_type_id, user_id in cursor.fetchall():
            user_roles.append(UserRole(
                role=role,
                user=User.objects.get(pk=user_id),
                content_type=ContentType.objects.get(pk=content_type_id),
                object_id=object_pk
            )),
            batch_create(UserRole, user_roles)

    # Create any remaining roles
    batch_create(UserRole, user_roles, flush=True)


def does_table_exist(table_name):
    return table_name in connection.introspection.table_names()


def migrate_group_permissions_to_roles(apps, schema_editor):
    """
    Migration strategy:
    - Apply locked roles to the group that match the group's permission set.
    - If any permissions are left over after a role is applied add a role with a single
      permission to it to make up for each missing permission.

    Example:
    If a group has permissions:
        - galaxy.change_namespace
        - galaxy.upload_to_namespace
        - galaxy.delete_collection
        - galaxy.view_group
        - galaxy.view_user
        
    The following roles would get applied:
        - galaxy.collection_namespace_owner
        - _permission:galaxy.view_group
        - _permission:galaxy.view_user

    galaxy.collection_namespace_owner is applied because the user has all the permissions that match it.
    After applying galaxy.collection_namespace_owner, the view_group and view_group permissions are left 
    over so _permission:galaxy.view_group and _permission:galaxy.view_user are created for each
    missing permission and added to the group. _permision:<perm_name> roles will only have the
    a single permission in them for <perm_name>.

    Users with the ability to change the ownership of objects are given admin roles. For example
    if my group has galaxy.change_namespace permissions on namespace foo, but nothing else, give
    them the galaxy.collection_namespace_owner role because they can already escalate their permissions.
    """

    is_guardian_table_available = does_table_exist("guardian_groupobjectpermission")

    Group = apps.get_model("galaxy", "Group")
    GroupRole = apps.get_model("core", "GroupRole")
    Role = apps.get_model("core", "Role")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    group_roles = []

    # Group Permissions
    for group in Group.objects.filter(name__ne="system:partner-engineers"):
        group_roles.extend(get_global_group_permissions(group, Role, GroupRole, Permission))

        # Skip migrating object permissions if guardian is not installed.
        if is_guardian_table_available:
            group_roles.extend(
                get_object_group_permissions(group, Role, GroupRole, ContentType, Permission))

        batch_create(GroupRole, group_roles)

    # Create any remaining roles
    batch_create(GroupRole, group_roles, flush=True)


def migrate_user_permissions_to_roles(apps, schema_editor):
    """
    Migration Strategy:

    We only care about user permissions for container namespaces and tasks. Global permissions
    for users are not used, and they should be ignored if they exist. The only user permissions
    that the system uses are ones that get automatically added for users that create tasks and
    container namespaces, so these are the only permissions that will get migrated to roles here.
    """

    # Skip the migration if the guardian permission tables don't exist.
    if not does_table_exist("guardian_userobjectpermission"):
        return

    Permission = apps.get_model("auth", "Permission")
    Role = apps.get_model("core", "Role")
    UserRole = apps.get_model("core", "UserRole")
    ContentType = apps.get_model("contenttypes", "ContentType")
    User = apps.get_model(settings.AUTH_USER_MODEL)

    # Get all users with change_containernamespace permissions. Change container namespace allows
    # users to set permissions on container namespaces, so it allows us to use it as a proxy for
    # users that have administrative rights on container namespace and we can just give them the
    # execution environment admin role.
    change_container_namespace = Permission.objects.get(
        codename="change_containernamespace", content_type__app_label="container")
    container_namespace_admin, _ = Role.objects.get_or_create(
        name="galaxy.execution_environment_namespace_owner", locked=True)
    add_object_role_for_users_with_permission(
        container_namespace_admin, change_container_namespace, UserRole, ContentType, User)

    # When tasks are created pulp adds delete task and a few other permissions to the user that
    # initiates the task. Delete task is a good proxy for this role.
    delete_task = Permission.objects.get(
        codename="view_task", content_type__app_label="core")
    task_owner, _ = Role.objects.get_or_create(name="galaxy.task_admin", locked=True)
    add_object_role_for_users_with_permission(
        task_owner, delete_task, UserRole, ContentType, User)


def edit_guardian_tables(apps, schema_editor):
    """
    Remove foreign key constraints in the guardian tables
    guardian_groupobjectpermission and guardian_userobjectpermission.

    This allows for objects in other tables to be deleted without
    violating these foreign key constraints.

    This also allows for the these tables to remain in the database for reference purposes.
    """

    tables_to_edit = ["guardian_groupobjectpermission", "guardian_userobjectpermission"]
    for table in tables_to_edit:
        if not does_table_exist(table):
            continue

        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, table)
            fk_constraints = [k for (k,v) in constraints.items() if v["foreign_key"]]
            for name in fk_constraints:
                cursor.execute(
                    f"ALTER TABLE {table} DROP CONSTRAINT {name};"
                )                


def clear_model_permissions(apps, schema_editor):
    """
    Clear out the old model level permission assignments.
    """

    Group = apps.get_model("galaxy", "Group")
    User = apps.get_model(settings.AUTH_USER_MODEL)

    Group.permissions.through.objects.all().delete()
    User.user_permissions.through.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("galaxy", "0028_update_synclist_model"),
    ]

    operations = [
        migrations.RunPython(
            code=migrate_group_permissions_to_roles, reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            code=migrate_user_permissions_to_roles, reverse_code=migrations.RunPython.noop
        ),
        migrations.RunPython(
            code=edit_guardian_tables, reverse_code=migrations.RunPython.noop
        ),
        migrations.RunPython(
            code=clear_model_permissions, reverse_code=migrations.RunPython.noop
        ),
    ]