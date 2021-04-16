from django.contrib.auth import password_validation
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from galaxy_ng.app.models import auth as auth_models


class GroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = auth_models.Group
        fields = (
            'id',
            'name'
        )


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = auth_models.User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'groups',
            'password',
            'date_joined',
            'is_superuser'
        )
        extra_kwargs = {
            'date_joined': {'read_only': True},
            'password': {'write_only': True, 'allow_blank': True, 'required': False}
        }

    def validate_password(self, password):
        if password:
            password_validation.validate_password(password)
            return password

    def validate_groups(self, groups):
        request_user = self.context['request'].user

        group_set = set(groups)
        instance_group_set = set()
        if self.instance:
            instance_group_set = set(list(self.instance.groups.all()))

        group_difference = instance_group_set.symmetric_difference(group_set)

        if not request_user.has_perm('galaxy.change_group'):
            authed_user_groups = request_user.groups.all()
            for g in group_difference:
                if not authed_user_groups.filter(pk=g.id).exists():
                    raise ValidationError(detail={
                        "groups": "'galaxy.change_group' permission is required to change"
                                  " a users group that the requesting user is not in."
                    })

        return groups

    def validate_is_superuser(self, data):
        request_user = self.context['request'].user
        if request_user.is_superuser != data:
            if not request_user.is_superuser:
                raise ValidationError(detail={
                    "is_superuser": "Must be a super user to grant super user permissions."
                })

        return data

    def _set_password(self, instance, data):
        # password doesn't get set the same as other data, so delete it
        # before the serializer saves
        password = data.pop('password', None)
        if password:
            instance.set_password(password)
        return instance

    def create(self, data):
        instance = super().create(data)
        instance = self._set_password(instance, data)
        instance.save()
        return instance

    def update(self, instance, data):
        instance = self._set_password(instance, data)
        return super().update(instance, data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['groups'] = GroupSerializer(instance.groups.all(), many=True).data
        return representation

    def to_internal_value(self, data):
        groups = data.get('groups')
        if groups:
            group_ids = []
            for group in groups:
                group_filter = {}
                for field in group:
                    if field in ('id', 'name'):
                        group_filter[field] = group[field]
                try:
                    group = auth_models.Group.objects.get(**group_filter)
                    group_ids.append(group.id)
                except auth_models.Group.DoesNotExist:
                    raise ValidationError(detail={
                        'groups': "Group name=%s, id=%s does not exist" % (group.get('name'),
                                                                           group.get('id'))})
                except ValueError:
                    raise ValidationError(detail={'group': 'Invalid group name or ID'})
            data['groups'] = group_ids
        return super().to_internal_value(data)


class CurrentUserSerializer(UserSerializer):
    model_permissions = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = auth_models.User
        fields = UserSerializer.Meta.fields + ('model_permissions',)
        extra_kwargs = dict(
            groups={'read_only': True},
            **UserSerializer.Meta.extra_kwargs
        )

    def get_model_permissions(self, obj):
        return {
            "add_namespace": obj.has_perm('galaxy.add_namespace'),
            "upload_to_namespace": obj.has_perm('galaxy.upload_to_namespace'),
            "change_namespace": obj.has_perm('galaxy.change_namespace'),
            "move_collection": obj.has_perm('ansible.modify_ansible_repo_content'),
            "change_remote": obj.has_perm('ansible.change_collectionremote'),
            "delete_remote": obj.has_perm('ansible.delete_collectionremote'),
            "add_remote": obj.has_perm('ansible.add_collectionremote'),
            "change_distribution": obj.has_perm('ansible.change_ansibledistribution'),
            "delete_distribution": obj.has_perm('ansible.delete_ansibledistribution'),
            "add_distribution": obj.has_perm('ansible.add_ansibledistribution'),
            "view_distribution": obj.has_perm('ansible.view_ansibledistribution'),
            "view_user": obj.has_perm('galaxy.view_user'),
            "delete_user": obj.has_perm('galaxy.delete_user'),
            "change_user": obj.has_perm('galaxy.change_user'),
            "add_user": obj.has_perm('galaxy.add_user'),
            "add_group": obj.has_perm('galaxy.add_group'),
            "delete_group": obj.has_perm('galaxy.delete_group'),
            "change_group": obj.has_perm('galaxy.change_group'),
            "view_group": obj.has_perm('galaxy.view_group'),
        }
