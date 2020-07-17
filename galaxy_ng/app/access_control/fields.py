from django.contrib.auth.models import Permission
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from galaxy_ng.app.models import auth as auth_models


class GroupPermissionField(serializers.Field):
    def to_representation(self, value):
        rep = []
        for group in value:
            rep.append({
                'id': group.id,
                'name': group.name,
                'object_permissions': value[group]
            })
        return rep

    def to_internal_value(self, data):
        internal = {}
        for group_data in data:
            perms = group_data['object_permissions']

            # validate that the permissions exist
            for perm in perms:
                permission_components = perm.split('.')
                filter = {}
                if len(permission_components) == 2:
                    filter = {
                        "content_type__app_label": permission_components[0],
                        "codename": permission_components[1]
                    }
                else:
                    filter = {
                        "codename": permission_components[0]
                    }

                if not Permission.objects.filter(**filter).exists():
                    raise ValidationError(detail={
                        'groups': 'Permission {} does not exist'.format(perm)})

            del group_data['object_permissions']
            try:
                group = auth_models.Group.objects.get(**group_data)
                internal[group] = perms
            except auth_models.Group.DoesNotExist:
                raise ValidationError(detail={
                    'groups': "Group name=%s, id=%s does not exist" % (group_data.get('name'),
                                                                       group_data.get('id'))})
            except ValueError:
                raise ValidationError(detail={'group': 'Invalid group name or ID'})

        return internal
