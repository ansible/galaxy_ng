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

    def update(self, instance, data):
        # password doesn't get set the same as other data, so delete it
        # before the serializer saves
        if 'password' in data:
            print(data)
            password = data.pop('password')
            print(password)
            print(data)
            if password:
                instance.set_password(password)

        return super().update(instance, data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['groups'] = GroupSerializer(instance.groups.all(), many=True).data
        return representation

    def to_internal_value(self, data):
        groups = data.get('groups')
        if groups:
            new_groups = []
            groups = GroupSerializer(data=groups, many=True)
            groups.is_valid(raise_exception=True)
            for group in groups.validated_data:
                new_groups.append(group['id'])
            data['groups'] = new_groups
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
