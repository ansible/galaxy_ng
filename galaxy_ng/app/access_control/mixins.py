from django.db import transaction
from django.core.exceptions import BadRequest
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError

from pulpcore.plugin.util import (
    assign_role,
    remove_role,
    get_groups_with_perms_attached_roles
)

from django_lifecycle import hook


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
