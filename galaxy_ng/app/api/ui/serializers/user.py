from rest_framework.serializers import (
    ModelSerializer,
    CharField
)
from rest_framework.exceptions import ValidationError

from galaxy_ng.app.models import auth as auth_models


class UserSerializer(ModelSerializer):
    password_confirm = CharField(write_only=True, allow_blank=True)

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
            'password': {'write_only': True, 'allow_blank': True}
        }

    def validate_password(self, password):
        if (len(password) <= 10):
            raise ValidationError(detail={
                'password': "Password must be 10+ characters long"})
        if (password != self.initial_data['password_confirm']):
            raise ValidationError(detail={
                'password': "Passwords do no match"})
        return password

    def update(self, instance, data):
        if (data['password']):
            instance.set_password(data['password'])

        del data['password']
        return super().update(instance, data)
