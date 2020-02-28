from rest_framework import serializers


class CurrentUserSerializer(serializers.Serializer):
    is_partner_engineer = serializers.BooleanField()
