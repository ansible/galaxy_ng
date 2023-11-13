from rest_framework import serializers

from galaxy_ng.app.models import (
    CollectionSurvey,
    CollectionSurveyRollup,
    LegacyRoleSurvey,
    LegacyRoleSurveyRollup,
)

from galaxy_ng.app.utils.survey import SURVEY_FIELDS


class CollectionSurveySerializer(serializers.ModelSerializer):

    responses = serializers.SerializerMethodField()

    class Meta:
        model = CollectionSurvey
        fields = [
            'id',
            'created',
            'modified',
            'collection',
            'user',
            'responses'
        ]
    
    def get_responses(self, obj):
        return dict((k, getattr(obj, k)) for k in SURVEY_FIELDS)


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


class LegacyRoleSurveySerializer(serializers.ModelSerializer):

    responses = serializers.SerializerMethodField()

    class Meta:
        model = LegacyRoleSurvey
        fields = [
            'id',
            'created',
            'modified',
            'role',
            'user',
            'responses',
        ]

    def get_responses(self, obj):
        return dict((k, getattr(obj, k)) for k in SURVEY_FIELDS)


class LegacyRoleSurveyRollupSerializer(serializers.ModelSerializer):

    namespace = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = LegacyRoleSurveyRollup
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
