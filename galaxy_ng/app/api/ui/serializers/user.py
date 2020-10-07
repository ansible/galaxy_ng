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
            'is_superuser',
        )
        extra_kwargs = {
            'date_joined': {'read_only': True},
            'password': {'write_only': True, 'allow_blank': True, 'required': False}
        }

    def validate_password(self, password):
        if password:
            password_validation.validate_password(password)
            return password

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
        representation['groups'] = GroupSerializer(
            instance.groups.all(), many=True).data
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
    is_partner_engineer = serializers.SerializerMethodField()
    model_permissions = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = auth_models.User
        fields = UserSerializer.Meta.fields + ('is_partner_engineer', 'model_permissions')
        extra_kwargs = dict(
            groups={'read_only': True},
            **UserSerializer.Meta.extra_kwargs
        )

    # TODO: Update UI to drop reliance on is_partner_engineer
    def get_is_partner_engineer(self, obj):
        return obj.has_perms([
            'galaxy.add_namespace',
            'galaxy.change_namespace',
            'galaxy.upload_to_namespace',
            'ansible.modify_ansible_repo_content',
            'ansible.change_collectionremote',
        ])

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
