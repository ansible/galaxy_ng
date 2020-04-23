from rest_framework.serializers import (
    ModelSerializer,
    CharField
)
from rest_framework.exceptions import ValidationError

from galaxy_ng.app.models import auth as auth_models


class GroupSerializer(ModelSerializer):

    class Meta:
        model = auth_models.Group
        fields = (
            'id',
            'name'
        )


class UserSerializer(ModelSerializer):
    password_confirm = CharField(write_only=True, allow_blank=True, required=False)

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
