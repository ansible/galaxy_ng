from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from pulp_ansible.app import viewsets as pulp_viewsets
from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    CollectionRemote,
)

from galaxy_ng.app.constants import COMMUNITY_DOMAINS
from galaxy_ng.app.api import utils


class AnsibleDistributionSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(source='pulp_created')
    updated_at = serializers.DateTimeField(source='pulp_last_updated')

    class Meta:
        model = AnsibleDistribution
        fields = (
            'name',
            'base_path',
            'content_guard',
            'created_at',
            'updated_at',
        )


class AnsibleRepositorySerializer(serializers.ModelSerializer):
    distributions = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='pulp_created')
    updated_at = serializers.DateTimeField(source='pulp_last_updated')

    last_sync_task = utils.RemoteSyncTaskField(source='remote')

    class Meta:
        model = AnsibleRepository
        fields = (
            'name',
            'description',
            'next_version',
            'distributions',
            'created_at',
            'updated_at',
            'last_sync_task',
        )

    @extend_schema_field(AnsibleDistributionSerializer(many=True))
    def get_distributions(self, obj):
        return [
            AnsibleDistributionSerializer(distro).data
            for distro in obj.distributions.all()
        ]


class CollectionRemoteSerializer(pulp_viewsets.CollectionRemoteSerializer):
    last_sync_task = utils.RemoteSyncTaskField(source='*')

    write_only_fields = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='pulp_created', required=False)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', required=False)

    proxy_password = serializers.CharField(
        help_text=_("Password for proxy authentication."),
        allow_null=True,
        required=False,
        style={'input_type': 'password'},
        write_only=True
    )
    proxy_username = serializers.CharField(
        help_text=_("User for proxy authentication."),
        allow_null=True,
        required=False,
        write_only=False,  # overwriting this as pulpcore defaults to True
    )
    token = serializers.CharField(
        allow_null=True,
        required=False,
        max_length=2000,
        write_only=True,
        style={'input_type': 'password'}
    )
    password = serializers.CharField(
        help_text=_("Remote password."),
        allow_null=True,
        required=False,
        style={'input_type': 'password'},
        write_only=True
    )
    username = serializers.CharField(
        help_text=_("Remote user."),
        allow_null=True,
        required=False,
        write_only=False,  # overwriting this as pulpcore defaults to True
    )
    name = serializers.CharField(read_only=True)
    repositories = serializers.SerializerMethodField()

    class Meta:
        model = CollectionRemote
        fields = (
            'pk',
            'name',
            'url',
            'auth_url',
            'token',
            'policy',
            'requirements_file',
            'created_at',
            'updated_at',
            'username',
            'password',
            'tls_validation',
            'client_key',
            'client_cert',
            'ca_cert',
            'last_sync_task',
            'repositories',
            'pulp_href',
            'download_concurrency',
            'proxy_url',
            'proxy_username',
            'proxy_password',
            'write_only_fields',
            'rate_limit',
            'signed_only',
        )
        extra_kwargs = {
            'name': {'read_only': True},
            'pulp_href': {'read_only': True},
            'client_key': {'write_only': True},
        }

    @extend_schema_field(serializers.ListField)
    def get_write_only_fields(self, obj):
        return utils.get_write_only_fields(self, obj)

    def validate(self, data):
        if not data.get('requirements_file') and any(
            [domain in data['url'] for domain in COMMUNITY_DOMAINS]
        ):
            raise serializers.ValidationError(
                detail={
                    'requirements_file':
                        _('Syncing content from community domains without specifying a '
                          'requirements file is not allowed.')
                }
            )

        init_data = self.initial_data
        if not data.get('proxy_password') and init_data.get('write_only_fields'):

            # filter proxy_password write_only_field
            proxy_pwd = next(
                item for item in init_data.get('write_only_fields')
                if item["name"] == "proxy_password"
            )
            repo = get_object_or_404(CollectionRemote, name=init_data.get('name'))

            # update proxy_password by value in db
            if proxy_pwd.get('is_set') and repo:
                data['proxy_password'] = repo.proxy_password

        return super().validate(data)

    @extend_schema_field(AnsibleRepositorySerializer(many=True))
    def get_repositories(self, obj):
        return [
            AnsibleRepositorySerializer(repo).data
            for repo in obj.repository_set.all()
        ]
