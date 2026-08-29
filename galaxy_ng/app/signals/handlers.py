"""
Signal handlers for the Galaxy application.
Those signals are loaded by
galaxy_ng.app.__init__:PulpGalaxyPluginAppConfig.ready() method.
"""

import threading
import contextlib
import logging

from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db.models.signals import post_delete
from django.db.models.signals import m2m_changed
from django.db.models import CharField, Value
from django.db.models.functions import Concat
from django.contrib.auth.models import Group
from django.conf import settings
from rest_framework.exceptions import ValidationError
from django.apps import apps
from django.utils.translation import gettext_lazy as _
from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    Collection,
    AnsibleNamespaceMetadata,
)
from galaxy_ng.app.constants import ROLE_DESCRIPTION
from galaxy_ng.app.models import Namespace, User, Team
from galaxy_ng.app.migrations._dab_rbac import copy_roles_to_role_definitions
from pulpcore.plugin.models import ContentRedirectContentGuard

from ansible_base.rbac.validators import validate_permissions_for_model
from ansible_base.rbac.models import (
    DABContentType,
    RoleDefinition,
    RoleUserAssignment,
    RoleTeamAssignment,
)
from ansible_base.rbac.triggers import dab_post_migrate
from ansible_base.rbac.triggers import (
    dab_rbac_assignments_created,
    dab_rbac_assignments_pre_delete,
)
from ansible_base.rbac import permission_registry
from ansible_base.resource_registry.signals.handlers import no_reverse_sync

from pulpcore.plugin.util import assign_role
from pulpcore.plugin.util import remove_role
from pulpcore.plugin.models.role import GroupRole, UserRole, Role


logger = logging.getLogger(__name__)


PULP_TO_ROLEDEF = {
    'galaxy.auditor': 'Platform Auditor',
}


ROLEDEF_TO_PULP = {
    'Platform Auditor': 'galaxy.auditor',
}


@receiver(post_save, sender=AnsibleRepository)
def ensure_retain_repo_versions_on_repository(sender, instance, created, **kwargs):
    """Ensure repository has retain_repo_versions set when created.
    retain_repo_versions defaults to 1 when not set.
    """

    if created and instance.retain_repo_versions is None:
        instance.retain_repo_versions = 1
        instance.save()


@receiver(post_save, sender=AnsibleDistribution)
def ensure_content_guard_exists_on_distribution(sender, instance, created, **kwargs):
    """Ensure distribution have a content guard when created."""

    content_guard = ContentRedirectContentGuard.objects.first()

    if created and instance.content_guard is None:
        instance.content_guard = content_guard
        instance.save()


@receiver(post_save, sender=Collection)
def create_namespace_if_not_present(sender, instance, created, **kwargs):
    """Ensure Namespace object exists when Collection object saved.
    django signal for pulp_ansible Collection model, so that whenever a
    Collection object is created or saved, it will create a Namespace object
    if the Namespace does not already exist.
    Supports use case: In pulp_ansible sync, when a new collection is sync'd
    a new Collection object is created, but the Namespace object is defined
    in galaxy_ng and therefore not created. This signal ensures the
    Namespace is created.
    """

    Namespace.objects.get_or_create(name=instance.namespace)


@receiver(post_save, sender=AnsibleNamespaceMetadata)
def associate_namespace_metadata(sender, instance, created, **kwargs):
    """
    Update the galaxy namespace when a new pulp ansible namespace
    object is added to the system.
    """

    ns, ns_created = Namespace.objects.get_or_create(name=instance.name)
    ns_metadata = ns.last_created_pulp_metadata

    def _update_metadata():
        ns.last_created_pulp_metadata = instance
        ns.company = instance.company
        ns.email = instance.email
        ns.description = instance.description
        ns.resources = instance.resources
        ns.set_links([{"name": x, "url": instance.links[x]} for x in instance.links])
        ns.save()

    if ns_created or ns_metadata is None or ns.metadata_sha256 != instance.metadata_sha256:
        _update_metadata()


# ___ DAB RBAC ___

# These roles should NOT sync to Pulp
TEAM_ROLES = ['Team Member', 'Team Admin']


def create_managed_roles(*args, **kwargs) -> None:
    # do not create corresponding roles for these RoleDefinitions
    with dab_rbac_signals(), no_reverse_sync():
        # Roles are migrated to resource server in migration script, post_migrate too early
        # Create the DAB-only roles
        permission_registry.create_managed_roles(apps)
        # Create any roles created by pulp post_migrate signals
        copy_roles_to_role_definitions(apps, None)


dab_post_migrate.connect(create_managed_roles, dispatch_uid="create_managed_roles")


# Signals for synchronizing the pulp roles with DAB RBAC roles
rbac_state = threading.local()

rbac_state.pulp_action = False
rbac_state.dab_action = False


@contextlib.contextmanager
def pulp_rbac_signals():
    "Used while firing signals from pulp RBAC models to avoid infinite loops"
    try:
        prior_value = rbac_state.pulp_action
        rbac_state.pulp_action = True
        yield
    finally:
        rbac_state.pulp_action = prior_value


@contextlib.contextmanager
def dab_rbac_signals():
    "Used while firing signals from DAB RBAC models to avoid infinite loops"
    try:
        prior_value = rbac_state.dab_action
        rbac_state.dab_action = True
        yield
    finally:
        rbac_state.dab_action = prior_value


def rbac_signal_in_progress():
    return bool(rbac_state.dab_action or rbac_state.pulp_action)


def pulp_role_to_single_content_type_or_none(pulprole):
    content_types = {perm.content_type for perm in pulprole.permissions.all()}
    if len(content_types) == 1:
        return next(iter(content_types))
    return None


def copy_permissions_role_to_role(roleA, roleB):
    """Make permissions on roleB match roleA

    Our RoleDefinition and Role models, and respective permission models,
    are similiar enough to use a shortcut.
    Without knowing the type of roleA or roleB, we can inspect permission codenames
    and then just make sure they match.

    A call to this method establishes that roleA should become the source-of-truth
    """
    permissionsA = list(roleA.permissions.prefetch_related("content_type"))
    permissionsB = list(roleB.permissions.prefetch_related("content_type"))
    fullnamesA = {f"{perm.content_type.app_label}.{perm.codename}" for perm in permissionsA}
    fullnamesB = {f"{perm.content_type.app_label}.{perm.codename}" for perm in permissionsB}
    fullnames_to_add = fullnamesA - fullnamesB
    fullnames_to_remove = fullnamesB - fullnamesA
    concat_exp = Concat("content_type__app_label", Value("."), "codename", output_field=CharField())

    # The m2m manager needs ids or objects so we need to work with the destination permission model
    # Optimization node: this should never simultaneously have both additions AND removals,
    # so there is no point in optimizing for that case
    permission_modelB = roleB._meta.get_field("permissions").related_model
    if fullnames_to_add:
        ids_to_add = list(
            permission_modelB.objects.annotate(fullname=concat_exp)
            .filter(fullname__in=fullnames_to_add)
            .values_list("id", flat=True)
        )
        roleB.permissions.add(*ids_to_add)

    if fullnames_to_remove:
        ids_to_remove = list(
            permission_modelB.objects.annotate(fullname=concat_exp)
            .filter(codename__in=fullnames_to_remove)
            .values_list("id", flat=True)
        )
        roleB.permissions.remove(*ids_to_remove)


# Pulp Role to DAB RBAC RoleDefinition objects
@receiver(post_save, sender=Role)
def copy_role_to_role_definition(sender, instance, created, **kwargs):
    """When a dab role is granted to a user, grant the equivalent pulp role."""
    if rbac_signal_in_progress():
        return
    with pulp_rbac_signals():
        roledef_name = PULP_TO_ROLEDEF.get(instance.name, instance.name)
        content_type = pulp_role_to_single_content_type_or_none(instance)
        description = _(instance.description or ROLE_DESCRIPTION.get(instance.name, instance.name))
        rd, rd_created = RoleDefinition.objects.get_or_create(
            name=roledef_name,
            defaults={
                'managed': instance.locked,
                'content_type': content_type,
                'description': description,
            }
        )
        if rd_created:
            logger.info(
                f'CREATE ROLEDEF name:{roledef_name}'
                + f' managed:{instance.locked} ctype:{content_type}'
            )
        else:
            # Update existing RoleDefinition if values have changed
            updated_fields = []
            description = _(
                instance.description or ROLE_DESCRIPTION.get(instance.name, instance.name)
            )
            if rd.managed != instance.locked:
                rd.managed = instance.locked
                updated_fields.append('managed')
            if rd.content_type != content_type and isinstance(content_type, DABContentType):
                rd.content_type = content_type
                updated_fields.append('content_type')
            if rd.description != description:
                rd.description = description
                updated_fields.append('description')

            if updated_fields:
                rd.save(update_fields=updated_fields)
                logger.info(
                    f'UPDATE ROLEDEF name:{roledef_name} fields:{updated_fields}'
                )


@receiver(post_delete, sender=Role)
def delete_role_to_role_definition(sender, instance, **kwargs):
    """When a dab role is granted to a user, grant the equivalent pulp role."""
    if rbac_signal_in_progress():
        return
    with dab_rbac_signals():
        roledef_name = PULP_TO_ROLEDEF.get(instance.name, instance.name)
        rd = RoleDefinition.objects.filter(name=roledef_name).first()
        if rd:
            rd.delete()


def copy_permission_role_to_rd(instance, action, model, pk_set, reverse, **kwargs):
    if rbac_signal_in_progress():
        return
    if action.startswith("pre_"):
        return
    if reverse:
        # NOTE: this should not work because of DAB RBAC signals either
        # but this exception should alert us to any problems via downstream testing
        # hopefully, if that is generalized
        raise RuntimeError(
            "Removal of permissions through reverse relationship"
            + " not supported due to galaxy_ng signals"
        )

    roledef_name = PULP_TO_ROLEDEF.get(instance.name, instance.name)
    rd = RoleDefinition.objects.filter(name=roledef_name).first()
    if rd:
        copy_permissions_role_to_role(instance, rd)


m2m_changed.connect(copy_permission_role_to_rd, sender=Role.permissions.through)


# DAB RBAC RoleDefinition objects to Pulp Role objects


@receiver(post_save, sender=RoleDefinition)
def copy_role_definition_to_role(sender, instance, created, **kwargs):
    """When a dab role is granted to a user, grant the equivalent pulp role."""
    if rbac_signal_in_progress():
        return
    with dab_rbac_signals():
        role_name = ROLEDEF_TO_PULP.get(instance.name, instance.name)
        role = Role.objects.filter(name=role_name).first()
        if not role:
            Role.objects.create(name=role_name, locked=instance.managed)
        # TODO(jctanner): other fields? like description


@receiver(post_delete, sender=RoleDefinition)
def delete_role_definition_to_role(sender, instance, **kwargs):
    """When a dab role is granted to a user, grant the equivalent pulp role."""
    if rbac_signal_in_progress():
        return
    with dab_rbac_signals():
        role_name = ROLEDEF_TO_PULP.get(instance.name, instance.name)
        role = Role.objects.filter(name=role_name).first()
        if role:
            role.delete()


def copy_permission_rd_to_role(instance, action, model, pk_set, reverse, **kwargs):
    if rbac_signal_in_progress():
        return
    if action.startswith("pre_"):
        return
    if reverse:
        # NOTE: this should not work because of DAB RBAC signals either
        # but this exception should alert us to any problems via downstream testing
        #  hopefully, if that is generalized
        raise RuntimeError(
            "Removal of permissions through reverse relationship"
            + " not supported due to galaxy_ng signals"
        )

    role_name = ROLEDEF_TO_PULP.get(instance.name, instance.name)
    role = Role.objects.filter(name=role_name).first()
    if role:
        copy_permissions_role_to_role(instance, role)


m2m_changed.connect(copy_permission_rd_to_role, sender=RoleDefinition.permissions.through)


# Pulp UserRole and TeamRole to DAB RBAC assignments


def lazy_content_type_correction(rd, obj):
    """Implements special behavior because pulp roles have no content type

    So this will apply the content_type of the first object given an object-assignment
    only under certain non-conflicting conditions"""
    if (obj is None) or rd.content_type_id:
        # If this is a system role assignment, or has already been corrected,
        # then nothing needs to be corrected
        return

    if rd.name in settings.ANSIBLE_BASE_JWT_MANAGED_ROLES:
        return
    if ((obj is None) and (rd.content_type_id is None)) or \
            (rd.content_type_id and obj._meta.model_name == rd.content_type.model):
        return  # type already matches with intent, so nothing to do here, do not even log
    if not rd.user_assignments.exists():
        ct = permission_registry.content_type_model.objects.get_for_model(obj)
        try:
            # If permissions will not pass the validator, then we do not want to do this
            validate_permissions_for_model(list(rd.permissions.all()), ct)
        except ValidationError as exc:
            logger.warning(
                f'Assignment to {rd.name} for {type(obj)}'
                + f' violates a DAB role validation rule: {exc}'
            )
            return
        rd.content_type = ct
        rd.save(update_fields=['content_type'])
    else:
        logger.warning(
            f'Assignment to {rd.name} for {type(obj)}'
            + ' mis-matches with existing assignments'
        )


@receiver(post_save, sender=UserRole)
def copy_pulp_user_role(sender, instance, created, **kwargs):
    """When a pulp role is granted to a user, grant the equivalent dab role."""

    # FIXME(jctanner): this is a temporary workaround to allow on-demand
    #   assigment of task roles to users from pulpcore's AFTER_CREATE
    #   hook on the Task model which calls ...
    #   self.add_roles_for_object_creator("core.task_user_dispatcher")
    if instance.role.name == 'core.task_user_dispatcher':
        return

    if rbac_signal_in_progress():
        return
    with pulp_rbac_signals():
        roledef_name = PULP_TO_ROLEDEF.get(instance.role.name, instance.role.name)
        rd = RoleDefinition.objects.filter(name=roledef_name).first()
        if rd:
            if instance.content_object:
                lazy_content_type_correction(rd, instance.content_object)
                rd.give_permission(instance.user, instance.content_object)
            else:
                rd.give_global_permission(instance.user)


@receiver(post_delete, sender=UserRole)
def delete_pulp_user_role(sender, instance, **kwargs):
    if rbac_signal_in_progress():
        return
    with pulp_rbac_signals():
        roledef_name = PULP_TO_ROLEDEF.get(instance.role.name, instance.role.name)
        rd = RoleDefinition.objects.filter(name=roledef_name).first()
        if rd:
            if instance.content_object:
                try:
                    rd.remove_permission(instance.user, instance.content_object)
                except Exception as e:
                    logger.warning(e)
            else:
                try:
                    rd.remove_global_permission(instance.user)
                except Exception as e:
                    logger.warning(e)


@receiver(post_save, sender=GroupRole)
def copy_pulp_group_role(sender, instance, created, **kwargs):
    if rbac_signal_in_progress():
        return
    with pulp_rbac_signals():
        roledef_name = PULP_TO_ROLEDEF.get(instance.role.name, instance.role.name)
        rd = RoleDefinition.objects.filter(name=roledef_name).first()

        team = Team.objects.filter(group=instance.group)
        if rd and team.exists():
            team = team.first()
            # FIXME(jctanner): multi-type roledefs
            try:
                if instance.content_object:
                    rd.give_permission(team, instance.content_object)
                else:
                    rd.give_global_permission(team)
            except ValidationError as e:
                logger.error(e)


@receiver(post_delete, sender=GroupRole)
def delete_pulp_group_role(sender, instance, **kwargs):
    if rbac_signal_in_progress():
        return
    with pulp_rbac_signals():
        roledef_name = PULP_TO_ROLEDEF.get(instance.role.name, instance.role.name)
        rd = RoleDefinition.objects.filter(name=roledef_name).first()
        team = Team.objects.filter(group=instance.group)
        if rd and team.exists():
            team = team.first()
            # FIXME(jctanner): multi-type roledefs
            try:
                if instance.content_object:
                    rd.remove_permission(team, instance.content_object)
                else:
                    rd.remove_global_permission(team)
            except ValidationError as e:
                logger.error(e)


# DAB RBAC assignments to pulp UserRole TeamRole


def _get_pulp_role_kwargs(assignment):
    kwargs = {}
    if assignment.object_id:
        kwargs["obj"] = assignment.content_object
    if isinstance(assignment, RoleUserAssignment):
        entity = assignment.user
    elif isinstance(assignment, RoleTeamAssignment):
        entity = assignment.team.group
    else:
        raise Exception(f"Could not find entity for DAB assignment {assignment}")
    role_name = ROLEDEF_TO_PULP.get(
        assignment.role_definition.name,
        assignment.role_definition.name
    )
    return (role_name, entity), kwargs


def _apply_dab_assignment(assignment, existing_role_names=None):
    role_name = ROLEDEF_TO_PULP.get(
        assignment.role_definition.name,
        assignment.role_definition.name
    )
    # some platform roles will not have matching pulp roles. When ``existing_role_names``
    # is supplied (the batch path) membership is checked against the pre-resolved set to
    # avoid a per-row query; otherwise fall back to a direct existence check.
    if existing_role_names is not None:
        role_exists = role_name in existing_role_names
    else:
        role_exists = Role.objects.filter(name=role_name).exists()
    if not role_exists:
        return
    args, kwargs = _get_pulp_role_kwargs(assignment)
    assign_role(*args, **kwargs)


def _unapply_dab_assignment(assignment, existing_role_names=None):
    role_name = ROLEDEF_TO_PULP.get(
        assignment.role_definition.name,
        assignment.role_definition.name
    )
    # See _apply_dab_assignment for the ``existing_role_names`` fast path.
    if existing_role_names is not None:
        role_exists = role_name in existing_role_names
    else:
        role_exists = Role.objects.filter(name=role_name).exists()
    if not role_exists:
        return
    args, kwargs = _get_pulp_role_kwargs(assignment)
    remove_role(*args, **kwargs)


def _existing_pulp_role_names(assignments):
    """Resolve, in a single query, which of a batch's roles exist as Pulp Roles.

    Returns the subset of the batch's mapped Pulp role names that actually exist as
    ``Role`` objects, so the per-row apply/unapply helpers can check set membership
    instead of issuing one ``exists()`` query each.
    """
    names = set()
    for assignment in assignments:
        role_name = ROLEDEF_TO_PULP.get(
            assignment.role_definition.name,
            assignment.role_definition.name
        )
        # Guard against non-string names (e.g. unspec'd mocks) reaching the DB query.
        if isinstance(role_name, str):
            names.add(role_name)
    if not names:
        return set()
    return set(Role.objects.filter(name__in=names).values_list("name", flat=True))


def _surviving_team_membership(team_user_assignments, batch_pks):
    """Return the ``(user_id, object_id)`` pairs that still have a team-role grant.

    One query for the whole batch: for the users/objects involved in the team-role
    user assignments being deleted, find which pairs still have a surviving team-role
    assignment (excluding the rows in this delete batch, whose DB rows still exist
    because the signal fires ``pre_delete``).
    """
    if not team_user_assignments:
        return set()
    user_ids = {instance.user_id for instance in team_user_assignments}
    object_ids = {instance.object_id for instance in team_user_assignments}
    return set(
        RoleUserAssignment.objects.filter(
            role_definition__name__in=TEAM_ROLES,
            user_id__in=user_ids,
            object_id__in=object_ids,
        ).exclude(pk__in=batch_pks).values_list("user_id", "object_id")
    )


def _content_object_for(instance, content_objects):
    """Resolve the content object for an assignment.

    Prefer the pre-fetched ``content_objects`` dict provided by the bulk signal
    (which is populated on the bulk_give/bulk_remove paths, including the JWT bulk
    path), and fall back to the assignment's own GFK ``content_object``.
    """
    if content_objects:
        obj = content_objects.get((instance.content_type_id, instance.object_id))
        if obj is not None:
            return obj
    return instance.content_object


def copy_dab_assignments(sender, assignments, content_objects, **kwargs):
    """Mirror a batch of newly-created DAB role assignments into Pulp / Django Groups.

    Connected to the DAB bulk ``dab_rbac_assignments_created`` signal, which fires once
    per grant operation for the whole batch -- including the JWT/SSO bulk_create path
    that skips Django's per-row ``post_save`` signal.

    The batch is inspected as a whole so the shared lookups run once: Pulp role
    existence is resolved in a single query, and team-role Group membership adds are
    coalesced per Django Group.
    """
    if rbac_signal_in_progress():
        return
    with dab_rbac_signals():
        existing_role_names = _existing_pulp_role_names(assignments)
        group_adds = {}  # group.pk -> (group, set(users))
        for instance in assignments:
            role_name = instance.role_definition.name
            if role_name in ('Organization Admin', 'Organization Member'):
                continue  # exception to not synchronize these roles to any old roles
            if role_name in TEAM_ROLES and isinstance(instance, RoleUserAssignment):
                # Add user to the team's Django Group to inherit all permissions
                # assigned to the team.
                group = _content_object_for(instance, content_objects).group
                group_adds.setdefault(group.pk, (group, set()))[1].add(instance.user)
                continue
            _apply_dab_assignment(instance, existing_role_names)
        for group, users in group_adds.values():
            group.user_set.add(*users)


def delete_dab_assignments(sender, assignments, content_objects, **kwargs):
    """Un-mirror a batch of to-be-deleted DAB role assignments from Pulp / Django Groups.

    Connected to the DAB bulk ``dab_rbac_assignments_pre_delete`` signal, which fires
    once per remove operation, before the rows are deleted, for the whole batch.

    Like the create handler, shared lookups run once per batch: Pulp role existence and
    the "another team-role grant survives" check are each a single query, and Group
    membership removals are coalesced per Django Group.
    """
    if rbac_signal_in_progress():
        return
    with dab_rbac_signals():
        existing_role_names = _existing_pulp_role_names(assignments)
        # PKs of the user assignments being deleted in this batch, so the "other
        # assignment survives" check can exclude rows that are themselves being removed
        # (their DB rows still exist because this is pre_delete).
        batch_pks = [
            instance.pk for instance in assignments
            if isinstance(instance, RoleUserAssignment)
        ]

        # Partition the batch: team-role user assignments un-mirror via Django Group
        # membership (resolved to (instance, group) pairs); everything else un-mirrors
        # from Pulp. A team assignment whose content object cannot be resolved falls
        # through to the Pulp path, matching the pre-batch behavior.
        team_group_ops = []  # list of (instance, group)
        to_unapply = []
        for instance in assignments:
            role_name = instance.role_definition.name
            if role_name in ('Organization Admin', 'Organization Member'):
                continue  # exception to not synchronize these roles to any old roles
            content_object = (
                _content_object_for(instance, content_objects)
                if role_name in TEAM_ROLES and isinstance(instance, RoleUserAssignment)
                else None
            )
            if content_object is not None:
                team_group_ops.append((instance, content_object.group))
            else:
                to_unapply.append(instance)

        for instance in to_unapply:
            _unapply_dab_assignment(instance, existing_role_names)

        survivors = _surviving_team_membership(
            [instance for instance, _group in team_group_ops], batch_pks
        )
        group_removes = {}  # group.pk -> (group, set(users))
        for instance, group in team_group_ops:
            # Only remove from group if no other team role assignment (that is not
            # itself part of this delete batch) still grants membership.
            if (instance.user_id, instance.object_id) in survivors:
                continue
            group_removes.setdefault(group.pk, (group, set()))[1].add(instance.user)
        for group, users in group_removes.values():
            group.user_set.remove(*users)


dab_rbac_assignments_created.connect(
    copy_dab_assignments, dispatch_uid='galaxy_dab_assignments_created'
)
dab_rbac_assignments_pre_delete.connect(
    delete_dab_assignments, dispatch_uid='galaxy_dab_assignments_pre_delete'
)


# Connect User.groups to the role in DAB

def copy_dab_group_to_role(instance, action, model, pk_set, reverse, **kwargs):
    if rbac_signal_in_progress():
        return
    if action.startswith("pre_"):
        return

    shared_member_rd = RoleDefinition.objects.get(name=TEAM_ROLES[0])
    if reverse:
        groups = [instance]
    else:
        if action == 'post_clear':
            qs = RoleUserAssignment.objects.filter(role_definition=shared_member_rd, user=instance)
            groups = [assignment.content_object.group for assignment in qs]
        else:
            groups = Group.objects.filter(pk__in=pk_set)

    # For every group affected by the change, assure that the DAB role assignments
    # are changed to match the users in the pulp group
    for group in groups:
        team = Team.objects.get(group_id=group.pk)
        current_dab_shared_members = {
            assignment.user for assignment in RoleUserAssignment.objects.filter(
                role_definition=shared_member_rd, object_id=team.pk
            )
        }
        current_pulp_members = set(group.user_set.all())
        not_allowed = current_dab_shared_members - current_pulp_members
        if not_allowed:
            usernames = ", ".join([u.username for u in not_allowed])
            logger.info(
                f'Can not remove users {usernames} from team {team.name}, '
                'because they are managed by the resource provider'
            )


m2m_changed.connect(copy_dab_group_to_role, sender=User.groups.through)
