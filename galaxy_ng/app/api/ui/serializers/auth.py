from rest_framework.serializers import CharField

from .base import Serializer


class LoginSerializer(Serializer):
    class Meta():
        ref_name = "galaxy.UILoginSerializer"

    username = CharField(required=True)
    password = CharField(required=True, style={'input_type': 'password'})
