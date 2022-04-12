import datetime
import time

from django.urls import include, path
from rest_framework import routers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination

from pulpcore.plugin.viewsets import OperationPostponedResponse
from pulpcore.plugin.tasking import dispatch
from pulpcore.app.models import Task
from pulpcore.plugin.models import ContentArtifact
from pulp_ansible.app.models import CollectionVersion
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app.api.v1.tasks import legacy_role_import
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole


class LegacyRoleSerializer(serializers.ModelSerializer):

    github_user = serializers.SerializerMethodField()
    github_repo = serializers.SerializerMethodField()
    github_branch = serializers.SerializerMethodField()
    commit = serializers.SerializerMethodField()
    summary_fields = serializers.SerializerMethodField()

    class Meta:
        model = LegacyRole
        fields = [
            'id',
            'created',
            'modified',
            'github_user',
            'github_repo',
            'github_branch',
            'commit',
            'name',
            'summary_fields'
        ]

    def get_id(self, obj):
        return obj.pulp_id

    def get_url(self, obj):
        return None

    def get_created(self, obj):
        return obj._created

    def get_modified(self, obj):
        return obj.pulp_created

    def get_github_user(self, obj):
        return obj.namespace.name

    def get_github_repo(self, obj):
        return obj.full_metadata.get('github_repo')

    def get_github_branch(self, obj):
        return obj.full_metadata.get('github_reference')

    def get_commit(self, obj):
        return obj.full_metadata.get('commit')

    def get_summary_fields(self, obj):
        versions = obj.full_metadata.get('versions', [])
        dependencies = obj.full_metadata.get('dependencies', [])
        tags = obj.full_metadata.get('tags', [])
        return {
            'dependencies': dependencies,
            'namespace': {
                'id': obj.namespace.id,
                'name': obj.namespace.name
            },
            'provider_namespace': {
                'id': obj.namespace.id,
                'name': obj.namespace.name
            },
            'repository': {
                'name': obj.name,
                'original_name': obj.full_metadata.get('github_repo')
            },
            'tags': tags,
            'versions': versions
        }

