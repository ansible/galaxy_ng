from rest_framework import serializers

from pulp_ansible.app import viewsets as pulp_viewsets
from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    CollectionRemote,
)

from galaxy_ng.app.constants import COMMUNITY_DOMAINS
from galaxy_ng.app.models.collectionsync import CollectionSyncTask


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


class LastSyncTaskMixin:

    def get_last_sync_task_queryset(self, obj):
        raise NotImplementedError("subclass must implement get_last_sync_task_queryset")

    def get_last_sync_task(self, obj):
        sync_task = self.get_last_sync_task_queryset(obj)
        if not sync_task:
            # UI handles `null` as "no status"
            return

        return {
            "task_id": sync_task.id,
            "state": sync_task.task.state,
            "started_at": sync_task.task.started_at,
            "finished_at": sync_task.task.finished_at,
            "error": sync_task.task.error
        }


class AnsibleRepositorySerializer(LastSyncTaskMixin, serializers.ModelSerializer):
    distributions = serializers.SerializerMethodField()
    last_sync_task = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='pulp_created')
    updated_at = serializers.DateTimeField(source='pulp_last_updated')

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

    def get_distributions(self, obj):
        return [
            AnsibleDistributionSerializer(distro).data
            for distro in obj.ansible_ansibledistribution.all()
        ]

    def get_last_sync_task_queryset(self, obj):
        return CollectionSyncTask.objects.filter(repository=obj).first()


class CollectionRemoteSerializer(LastSyncTaskMixin, pulp_viewsets.CollectionRemoteSerializer):
    last_sync_task = serializers.SerializerMethodField()
    write_only_fields = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='pulp_created', required=False)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', required=False)
    proxy_password = serializers.CharField(
        help_text="Password for proxy authentication.",
        allow_null=True,
        required=False,
        style={'input_type': 'password'},
        write_only=True
    )
    proxy_username = serializers.CharField(
        help_text="User for proxy authentication.",
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
        help_text="Remote password.",
        allow_null=True,
        required=False,
        style={'input_type': 'password'},
        write_only=True
    )
    username = serializers.CharField(
        help_text="Remote user.",
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
            'rate_limit'
        )
        extra_kwargs = {
            'name': {'read_only': True},
            'pulp_href': {'read_only': True},
            'client_key': {'write_only': True},
        }

    def validate(self, data):
        if not data.get('requirements_file') and any(
            [domain in data['url'] for domain in COMMUNITY_DOMAINS]
        ):
            raise serializers.ValidationError(
                detail={
                    'requirements_file':
                        'Syncing content from community domains without specifying a '
                        'requirements file is not allowed.'
                }
            )
        return super().validate(data)

    def get_write_only_fields(self, obj):
        return get_write_only_fields(self, obj)

    def get_repositories(self, obj):
        return [
            AnsibleRepositorySerializer(repo).data
            for repo in obj.repository_set.all()
        ]

    def get_last_sync_task_queryset(self, obj):
        """Gets last_sync_task from Pulp using remote->repository relation"""

        return CollectionSyncTask.objects.filter(
            repository=obj.repository_set.order_by('-pulp_last_updated').first()
        ).first()


def get_write_only_fields(serializer, obj, extra_data=None):
    """
    Returns a list of write only fields and whether or not their values are set
    so that clients can tell if they are overwriting an existing value.
    serializer: Serializer instance
    obj: model object being serialized
    extra_data: extra fields that might not be on obj. This is used when a write
        only field is not one of the fields in the underlying data model.
    """
    fields = []
    extra_data = extra_data or {}

    # returns false if field is "" or None
    def _is_set(field_name):
        if (field_name in extra_data):
            return bool(extra_data[field_name])
        else:
            return bool(getattr(obj, field_name))

    # There are two ways to set write_only. This checks both.

    # check for values that are set to write_only in Meta.extra_kwargs
    for field_name in serializer.Meta.extra_kwargs:
        if serializer.Meta.extra_kwargs[field_name].get('write_only', False):
            fields.append({"name": field_name, "is_set": _is_set(field_name)})

    # check for values that are set to write_only in fields
    serializer_fields = serializer.get_fields()
    for field_name in serializer_fields:
        if (serializer_fields[field_name].write_only):
            fields.append({"name": field_name, "is_set": _is_set(field_name)})

    return fields
