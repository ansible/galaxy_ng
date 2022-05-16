from collections import defaultdict

from django.db import transaction
from django.core.exceptions import BadRequest
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from rest_framework.exceptions import ValidationError

from pulpcore.plugin.util import (
    assign_role,
    remove_role,
    # get_groups_with_perms_attached_roles,
)

from pulpcore.plugin.models.role import GroupRole

from django_lifecycle import hook


# TODO: Replace this with the version from pulpcore once 
# https://github.com/pulp/pulpcore/pull/2728 is merged and released
def get_groups_with_perms_attached_roles(obj, only_with_perms_in=None):
    ctype = ContentType.objects.get_for_model(obj)
    perms = Permission.objects.filter(content_type__pk=ctype.id)
    if only_with_perms_in:
        codenames = [
            split_perm[-1]
            for split_perm in (perm.split(".", maxsplit=1) for perm in only_with_perms_in)
            if len(split_perm) == 1 or split_perm[0] == ctype.app_label
        ]
        perms = perms.filter(codename__in=codenames)
    group_roles = GroupRole.objects.filter(role__permissions__in=perms).filter(
        Q(content_type=ctype, object_id=obj.pk)
    )
    res = defaultdict(set)
    for group_role in group_roles:
        res[group_role.group].add(group_role.role.name)
    return {k: list(v) for k, v in res.items()}


class GroupModelPermissionsMixin:
    _groups = None

    @property
    def groups(self):
        return get_groups_with_perms_attached_roles(self)

    @groups.setter
    def groups(self, groups):
        self._set_groups(groups)

    @transaction.atomic
    def _set_groups(self, groups):
        # Can't add permissions to objects that haven't been
        # saved. When creating new objects, save group data to _groups where it
        # can be picked up by the post save hook.
        if self._state.adding:
            self._groups = groups
        else:
            current_groups = get_groups_with_perms_attached_roles(self)
            for group in current_groups:
                for perm in current_groups[group]:
                    remove_role(perm, group, self)

            for group in groups:
                for role in groups[group]:
                    try:
                        assign_role(role, group, self)
                    except BadRequest:
                        raise ValidationError(
                            detail={'groups': _('Role {role} does not exist or does not '
                                                'have any permissions related to this object.'
                                                ).format(role=role)}
                        )

    @hook('after_save')
    def set_object_groups(self):
        if self._groups:
            self._set_groups(self._groups)
