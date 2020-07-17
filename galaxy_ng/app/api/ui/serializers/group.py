from rest_framework import serializers

from galaxy_ng.app.models import auth as auth_models


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = auth_models.Group
        fields = (
            'id',
            'name',
        )
