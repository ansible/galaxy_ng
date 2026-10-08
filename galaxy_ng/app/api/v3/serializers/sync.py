from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from pulp_ansible.app import serializers as pulp_serializers
from pulp_ansible.app import viewsets as pulp_viewsets
from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    CollectionRemote,
)

from ansible_base.lib.serializers.mixins import CleanTextMixin
from ansible_base.lib.utils.validation import DEFAULT_NAME_FIELDS

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
    """Nested-read shape embedded on collection remotes GET.

    Not a drop-in for Pulp's repository API. Writable repository fields live on
    AnsibleRepositoryDetailSerializer, used by /_ui/v1/repositories/.
    """

    distributions = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='pulp_created', read_only=True)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', read_only=True)
    next_version = serializers.IntegerField(read_only=True)

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


class AnsibleRepositoryDetailSerializer(
    CleanTextMixin,
    utils.UniqueNameIntegrityMixin,
    pulp_serializers.AnsibleRepositorySerializer,
):
    """Galaxy write/detail serializer for /_ui/v1/repositories/.

    Subclasses pulp_ansible's serializer so create/edit accept the same form
    fields as /pulp/api/v3/repositories/ansible/ansible/ (private, remote,
    pulp_labels, retain_repo_versions, pulp_href). Nested remotes GET keeps
    the thinner AnsibleRepositorySerializer so that response shape is unchanged.
    """

    # ASCII-armored GPG material trips Tier 2 the same way remote certs do.
    excluded_fields = frozenset({'gpgkey'})

    distributions = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='pulp_created', read_only=True)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', read_only=True)
    next_version = serializers.IntegerField(read_only=True)
    last_sync_task = utils.RemoteSyncTaskField(source='remote')

    class Meta:
        model = AnsibleRepository
        fields = (
            *pulp_serializers.AnsibleRepositorySerializer.Meta.fields,
            'distributions',
            'created_at',
            'updated_at',
            'next_version',
        )

    def validate_name(self, value):
        utils.validate_unique_pulp_resource_name(
            AnsibleRepository, value, instance=self.instance,
        )
        return value

    @extend_schema_field(AnsibleDistributionSerializer(many=True))
    def get_distributions(self, obj):
        return [
            AnsibleDistributionSerializer(distro).data
            for distro in obj.distributions.all()
        ]


class CollectionRemoteSerializer(CleanTextMixin, pulp_viewsets.CollectionRemoteSerializer):
    # Credentials/certs aren't rendered anywhere and carry no XSS risk; excluding
    # them avoids false positives on PEM/base64 content unrelated to free text.
    excluded_fields = frozenset({
        'token', 'password', 'proxy_password', 'client_key', 'client_cert', 'ca_cert',
    })
    # `username` here authenticates against a third-party remote, not a Hub account,
    # so Tier 1's strict resource-name charset (no '+', ':', etc.) is too narrow for
    # arbitrary external usernames. Route it through Tier 2 (free-text) instead.
    name_fields = DEFAULT_NAME_FIELDS - {'username'}

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
    # Declared explicitly so this serializer loads on pulp-ansible versions
    # that do not yet have CollectionRemote.sync_highest_versions (e.g. 0.29.6).
    # Listing it only in Meta.fields makes DRF treat it as a model field and 500.
    sync_highest_versions = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )

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
            'sync_highest_versions',
        )
        extra_kwargs = {
            'name': {'read_only': True},
            'pulp_href': {'read_only': True},
            'client_key': {'write_only': True},
        }

    @extend_schema_field(serializers.ListField)
    def get_write_only_fields(self, obj):
        return utils.get_write_only_fields(self, obj)

    @staticmethod
    def _validated_write_only_fields(init_data):
        # write_only_fields is GET-shape metadata clients may echo on update.
        # When present it must be a list of dicts with string "name" keys
        # (same shape as get_write_only_fields). Reject malformed payloads with
        # 400 instead of crashing.
        if 'write_only_fields' not in init_data:
            return None
        write_only_fields = init_data.get('write_only_fields')
        if not isinstance(write_only_fields, list):
            raise serializers.ValidationError(
                {
                    'write_only_fields': _(
                        'Expected a list of objects with a string "name" field.'
                    )
                }
            )
        for item in write_only_fields:
            if not isinstance(item, dict) or not isinstance(item.get('name'), str):
                raise serializers.ValidationError(
                    {
                        'write_only_fields': _(
                            'Expected a list of objects with a string "name" field.'
                        )
                    }
                )
        return write_only_fields

    def validate(self, data):
        # On partial updates, absent fields keep their stored values. Check the
        # resulting url/requirements_file pair, not just the request payload —
        # otherwise clearing requirements_file alone skips the community-domain
        # guard, and a url-only PATCH rejects remotes that already have a file.
        if self.instance is not None:
            url = data.get('url', self.instance.url)
            requirements_file = data.get(
                'requirements_file', self.instance.requirements_file
            )
        else:
            url = data.get('url')
            requirements_file = data.get('requirements_file')

        if url and not requirements_file and any(
            domain in url for domain in COMMUNITY_DOMAINS
        ):
            raise serializers.ValidationError(
                detail={
                    'requirements_file':
                        _('Syncing content from community domains without specifying a '
                          'requirements file is not allowed.')
                }
            )

        # The proxy_password entry with is_set=true is a keep-hint: restore only
        # from the remote being edited (self.instance). The value stays in data
        # so PUT (partial=False) still satisfies pulpcore's proxy
        # username/password pairing check.
        write_only_fields = self._validated_write_only_fields(self.initial_data)
        if (
            self.instance
            and not data.get('proxy_password')
            and write_only_fields
        ):
            proxy_pwd = next(
                (
                    item for item in write_only_fields
                    if item.get('name') == 'proxy_password'
                ),
                None,
            )
            if proxy_pwd and proxy_pwd.get('is_set'):
                data['proxy_password'] = self.instance.proxy_password

        return super().validate(data)

    @extend_schema_field(AnsibleRepositorySerializer(many=True))
    def get_repositories(self, obj):
        return [
            AnsibleRepositorySerializer(repo).data
            for repo in obj.repository_set.all()
        ]


class CollectionRemoteCreateSerializer(CollectionRemoteSerializer):
    """Serializer used only for the create action on /_ui/v1/remotes/.

    Identical to CollectionRemoteSerializer except ``name`` is writable
    (and required) so the client can supply it when creating a new remote.
    The base serializer keeps ``name`` read-only to prevent renames on
    update and to keep the sync-config PUT endpoint backward-compatible.
    """
    name = serializers.CharField()

    def validate_name(self, value):
        utils.validate_unique_pulp_resource_name(CollectionRemote, value)
        return value
