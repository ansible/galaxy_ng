from rest_framework import serializers

from galaxy_ng.app.api.v1.models import (
    CollectionSurvey,
    CollectionSurveyRollup,
    LegacyRoleSurvey,
    LegacyRoleSurveyRollup,
)

from galaxy_ng.app.api.v1.utils.survey import SURVEY_FIELDS


class CollectionSurveySerializer(serializers.ModelSerializer):

    responses = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    collection = serializers.SerializerMethodField()

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

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username
        }

    def get_collection(self, obj):
        return {
            'id': obj.collection.pulp_id,
            'namespace': obj.collection.namespace,
            'name': obj.collection.name
        }

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
        return obj.collection.namespace

    def get_name(self, obj):
        return obj.collection.name


class LegacyRoleSurveySerializer(serializers.ModelSerializer):

    responses = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

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

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username
        }

    def get_role(self, obj):
        return {
            'id': obj.role.id,
            'namespace': obj.role.namespace.name,
            'name': obj.role.name
        }

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
