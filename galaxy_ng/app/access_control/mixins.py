from django.conf import settings
from django.db import transaction
from guardian.shortcuts import get_groups_with_perms, assign_perm, remove_perm
from django_lifecycle import hook


class GroupModelPermissionsMixin:
    _groups = None

    @property
    def groups(self):
        return get_groups_with_perms(self, attach_perms=True)

    @groups.setter
    def groups(self, groups):
        self._set_groups(groups)

    @transaction.atomic
    def _set_groups(self, groups):
        # guardian doesn't allow adding permissions to objects that haven't been
        # saved. When creating new objects, save group data to _groups where it
        # can be picked up by the post save hook.
        if self._state.adding:
            self._groups = groups
        else:
            current_groups = get_groups_with_perms(self, attach_perms=True)
            for group in current_groups:
                for perm in current_groups[group]:
                    remove_perm(perm, group, self)

            for group in groups:
                for perm in groups[group]:
                    assign_perm(perm, group, self)

    @hook('after_save')
    def set_object_groups(self):
        if self._groups:
            self._set_groups(self._groups)


class UnauthenticatedCollectionAccessMixin:
    def unauthenticated_collection_access_enabled(self, request, view, action):
        return settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS
