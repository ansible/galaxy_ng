from django.contrib.auth import password_validation
from rest_framework import serializers

from galaxy_ng.app.api import permissions
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
        )
        extra_kwargs = {
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
        representation['groups'] = GroupSerializer(instance.groups.all(), many=True).data
        return representation

    def to_internal_value(self, data):
        groups = data.get('groups')
        if groups:
            id_list = []
            for group in groups:
                if 'id' not in group:
                    raise serializers.ValidationError(
                        detail={'groups': 'List of dicts that contain at least an "id" key'})
                id_list.append(group['id'])
            data['groups'] = id_list
        return super().to_internal_value(data)


class CurrentUserSerializer(UserSerializer):
    is_partner_engineer = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = auth_models.User
        fields = UserSerializer.Meta.fields + ('is_partner_engineer',)
        extra_kwargs = dict(
            groups={'read_only': True},
            **UserSerializer.Meta.extra_kwargs
        )

    def get_is_partner_engineer(self, obj):
        return (
            obj.groups.filter(name=permissions.IsPartnerEngineer.GROUP_NAME).exists()
        )
