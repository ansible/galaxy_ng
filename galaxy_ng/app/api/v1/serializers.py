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


class LegacyUserSerializer(serializers.ModelSerializer):

    summary_fields = serializers.SerializerMethodField()
    date_joined = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    staff = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = LegacyNamespace
        fields = [
            'id',
            'url',
            'summary_fields',
            'created',
            'modified',
            'username',
            'staff',
            'full_name',
            'date_joined',
            'avatar_url',
            'active'
        ]

    def get_username(self, obj):
        return obj.name

    def get_url(self, obj):
        return ''

    def get_full_name(self, obj):
        return ''

    def get_date_joined(self, obj):
        return obj.created

    def get_summary_fields(self, obj):
        return {}

    def get_staff(self, obj):
        return False

    def get_active(self, obj):
        return True

    def get_avatar_url(self, obj):
        url = f'https://github.com/{obj.name}.png'
        return url


class LegacyRoleSerializer(serializers.ModelSerializer):

    github_user = serializers.SerializerMethodField()
    github_repo = serializers.SerializerMethodField()
    github_branch = serializers.SerializerMethodField()
    commit = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
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
            'description',
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

    def get_description(self, obj):
        return obj.full_metadata.get('description')

    def get_summary_fields(self, obj):
        versions = obj.full_metadata.get('versions', [])
        dependencies = obj.full_metadata.get('dependencies', [])
        tags = obj.full_metadata.get('tags', [])
        return {
            'dependencies': dependencies,
            'namespace': {
                'id': obj.namespace.id,
                'name': obj.namespace.name,
                'avatar_url': f'https://github.com/{obj.namespace.name}.png'
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


class LegacyRoleContentSerializer(serializers.ModelSerializer):

    readme = serializers.SerializerMethodField()
    readme_html = serializers.SerializerMethodField()

    class Meta:
        model = LegacyRole
        fields = [
            'readme',
            'readme_html'
        ]

    def get_readme(self, obj):
        return obj.full_metadata.get('readme', '')

    def get_readme_html(self, obj):
        return obj.full_metadata.get('readme_html', '')

