from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from pulpcore.plugin.models.role import Role

from pulpcore.plugin.util import get_perms_for_model

from galaxy_ng.app.models import auth as auth_models


class GroupPermissionField(serializers.Field):
    def _validate_group(self, group_data):
        if 'object_roles' not in group_data:
            raise ValidationError(detail={
                'groups': _('object_roles field is required')})

        if 'id' not in group_data and 'name' not in group_data:
            raise ValidationError(detail={
                'groups': _('id or name field is required')})

        roles = group_data['object_roles']

        if not isinstance(roles, list):
            raise ValidationError(detail={
                'groups': _('object_roles must be a list of strings')})

        # validate that the permissions exist
        for role in roles:
            # TODO(newswangerd): Figure out how to make this one SQL query instead of
            # performing N queries for each permission
            if not Role.objects.filter(name=role).exists():
                raise ValidationError(detail={
                    'groups': _('Role {} does not exist').format(role)})

    def to_representation(self, value):
        rep = []
        for group in value:
            rep.append({
                'id': group.id,
                'name': group.name,
                'object_roles': value[group]
            })
        return rep

    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise ValidationError(detail={
                'groups': _('Groups must be a list of group objects')
            })

        internal = {}
        for group_data in data:
            self._validate_group(group_data)
            group_filter = {}
            for field in group_data:
                if field in ('id', 'name'):
                    group_filter[field] = group_data[field]
            try:
                group = auth_models.Group.objects.get(**group_filter)
                if 'object_permissions' in group_data:
                    internal[group] = group_data['object_permissions']
                if 'object_roles' in group_data:
                    internal[group] = group_data['object_roles']
            except auth_models.Group.DoesNotExist:
                raise ValidationError(detail={
                    'groups': _("Group name=%s, id=%s does not exist") % (
                        group_data.get('name'), group_data.get('id'))
                })
            except ValueError:
                raise ValidationError(detail={'group': _('Invalid group name or ID')})

        return internal


class MyPermissionsField(serializers.Serializer):
    def to_representation(self, original_obj):
        request = self.context.get('request', None)
        if request is None:
            return []
        user = request.user

        if original_obj._meta.proxy:
            obj = original_obj._meta.concrete_model.objects.get(pk=original_obj.pk)
        else:
            obj = original_obj

        my_perms = []
        for perm in get_perms_for_model(type(obj)).all():
            codename = "{}.{}".format(perm.content_type.app_label, perm.codename)
            if user.has_perm(codename) or user.has_perm(codename, obj):
                my_perms.append(codename)

        return my_perms
