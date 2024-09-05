from rest_framework.serializers import CharField

from .base import Serializer


class LoginSerializer(Serializer):
    username = CharField(required=True)
    password = CharField(required=True, style={'input_type': 'password'})
