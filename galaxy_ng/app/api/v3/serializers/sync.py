from rest_framework import serializers
from pulp_ansible.app.models import CollectionRemote
from pulp_ansible.app.viewsets import CollectionRemoteSerializer
from galaxy_ng.app.constants import COMMUNITY_DOMAINS, VALID_DISTRO_NAMES


class SyncConfigSerializer(CollectionRemoteSerializer):
    created_at = serializers.DateTimeField(source='pulp_created', required=False)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', required=False)

    class Meta:
        model = CollectionRemote
        fields = (
            'name',
            'url',
            'auth_url',
            'policy',
            'requirements_file',
            'created_at',
            'updated_at',
        )

    def validate(self, data):
        data = super().validate(data)
        errors = {}
        name = data['name']
        requirements_file = data['requirements_file']
        url = data['url']

        if name not in VALID_DISTRO_NAMES:
            errors['name'] = (
                f'{name} is not a valid name, possible values are {VALID_DISTRO_NAMES}'
            )

        if not requirements_file and any([domain in url for domain in COMMUNITY_DOMAINS]):
            errors['requirements_file'] = (
                'Syncing content from community domains without specifying a '
                'requirements file is not allowed.'
            )

        if errors:
            raise serializers.ValidationError(detail=errors)

        return data
