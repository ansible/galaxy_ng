from rest_framework.serializers import CharField

from galaxy_ng.app.api.ui.serializers.base import Serializer


class LoginSerializer(Serializer):
    username = CharField(required=True)
    password = CharField(required=True, style={'input_type': 'password'})
