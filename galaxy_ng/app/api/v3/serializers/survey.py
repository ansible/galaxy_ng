from rest_framework import serializers

from galaxy_ng.app.models import (
    CollectionSurveyRollup,
    LegacyRoleSurveyRollup,
)


class CollectionSurveyRollupSerializer(serializers.ModelSerializer):

    namespace = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = CollectionSurveyRollup
        fields = [
            'id',
            'created',
            'modified',
            'collection',
            'namespace',
            'name',
            'score'
        ]

    def get_namespace(self, obj):
        return obj.collection.namespace.name

    def get_name(self, obj):
        return obj.collection.name


class LegacyRoleSurveyRollupSerializer(serializers.ModelSerializer):

    namespace = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = CollectionSurveyRollup
        fields = [
            'id',
            'created',
            'modified',
            'role',
            'namespace',
            'name',
            'score'
        ]

    def get_namespace(self, obj):
        return obj.role.namespace.name

    def get_name(self, obj):
        return obj.role.name
