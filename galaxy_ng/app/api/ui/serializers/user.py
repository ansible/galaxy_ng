from rest_framework import serializers
from rest_framework.exceptions import ValidationError
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
    password_confirm = serializers.CharField(write_only=True, allow_blank=True, required=False)

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
            'password_confirm'
        )
        extra_kwargs = {
            'password': {'write_only': True, 'allow_blank': True, 'required': False}
        }

    def validate_password(self, password):
        if not password:
            return
        if len(password) <= 10:
            raise ValidationError(detail={
                'password': "Password must be 10+ characters long"})
        if password != self.initial_data['password_confirm']:
            raise ValidationError(detail={
                'password': "Passwords do no match"})
        return password

    def update(self, instance, data):
        if 'password' in data:
            if data['password']:
                instance.set_password(data['password'])

            # password doesn't get set the same as other data, so delete it
            # before the serializer saves
            del data['password']

        return super().update(instance, data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['groups'] = \
            GroupSerializer(instance.groups.all(), many=True).data
        return representation


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
