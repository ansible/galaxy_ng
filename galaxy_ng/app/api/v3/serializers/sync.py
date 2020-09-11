from rest_framework import serializers
from pulp_ansible.app.models import CollectionRemote
from pulp_ansible.app.viewsets import CollectionRemoteSerializer
from galaxy_ng.app.constants import COMMUNITY_DOMAINS


class SyncConfigSerializer(CollectionRemoteSerializer):
    created_at = serializers.DateTimeField(source='pulp_created', required=False)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', required=False)
    token = serializers.CharField(allow_null=True, required=False, max_length=2000, write_only=True)
    name = serializers.CharField(read_only=True)

    class Meta:
        model = CollectionRemote
        fields = (
            'name',
            'url',
            'auth_url',
            'token',
            'policy',
            'requirements_file',
            'created_at',
            'updated_at',
        )

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
