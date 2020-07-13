import logging

from pulp_ansible.app.models import CollectionVersion
from rest_framework import serializers

from .base import Serializer
from galaxy_ng.app.api.v3.serializers.namespace import NamespaceSummarySerializer


log = logging.getLogger(__name__)


class ContentSummarySerializer(Serializer):

    def to_representation(self, contents):
        summary = {"role": [], "module": [], "playbook": [], "plugin": []}
        for item in contents:
            key = self._get_content_type_key(item["content_type"])
            summary[key].append(item['name'])
        return {"total_count": sum(map(len, summary.items())), "contents": summary}

    @staticmethod
    def _get_content_type_key(content_type: str) -> str:
        # FIXME(cutwater): Replace with galaxy-importer constants usage
        if content_type == "role":  # ContentType.ROLE (from galaxy-importer)
            return "role"
        elif content_type == "module":  # ContentType.MODULE (from galaxy-importer)
            return "module"
        elif content_type == "playbook":  # ContentType.PLAYBOOK (from galaxy-importer)
            return "playbook"
        else:
            return "plugin"


class ContentSerializer(Serializer):
    name = serializers.CharField()
    content_type = serializers.CharField()
    description = serializers.CharField()


class CollectionVersionSummarySerializer(Serializer):
    version = serializers.CharField()
    created = serializers.CharField()


class CollectionMetadataSerializer(Serializer):
    dependencies = serializers.JSONField()
    contents = serializers.JSONField()

    # URLs
    documentation = serializers.CharField()
    homepage = serializers.CharField()
    issues = serializers.CharField()
    repository = serializers.CharField()

    description = serializers.CharField()
    authors = serializers.ListField(serializers.CharField())
    license = serializers.ListField(serializers.CharField())
    tags = serializers.SerializerMethodField()

    def get_tags(self, collection_version):
        # TODO(awcrosby): remove when galaxy_pulp no longer used in _ui
        if isinstance(collection_version, dict):
            return [tag['name'] for tag in collection_version['tags']]

        return [tag.name for tag in collection_version.tags.all()]


class CollectionVersionBaseSerializer(Serializer):
    namespace = serializers.CharField()
    name = serializers.CharField()
    version = serializers.CharField()
    certification = serializers.ChoiceField(
        ['certified', 'not_certified', 'needs_review'],
        required=True
    )
    metadata = CollectionMetadataSerializer(source='*')
    contents = serializers.ListField(ContentSerializer())

    created_at = serializers.DateTimeField(source='pulp_created')


class CollectionVersionSerializer(CollectionVersionBaseSerializer):
    repository_list = serializers.SerializerMethodField()

    def get_repository_list(self, collection_version):
        """Repository list where content is in the latest RepositoryVersion."""

        # get all repos where content exists in a RepositoryVersion
        content = collection_version.content_ptr
        all_repos = content.repositories.all().distinct()

        qs = CollectionVersion.objects.filter(pk=collection_version.pk)
        cv_in_repo_latest_version = []
        for repo in all_repos:
            if qs.filter(pk__in=repo.latest_version().content):
                cv_in_repo_latest_version.append(repo.name)
        return cv_in_repo_latest_version


class CertificationSerializer(Serializer):
    certification = serializers.ChoiceField(
        ['certified', 'not_certified', 'needs_review'])


class CollectionVersionDetailSerializer(CollectionVersionBaseSerializer):
    docs_blob = serializers.JSONField()


class _CollectionSerializer(Serializer):
    id = serializers.UUIDField()
    namespace = serializers.SerializerMethodField()
    name = serializers.CharField()
    download_count = serializers.IntegerField(default=0)
    latest_version = CollectionVersionBaseSerializer(source='*')
    deprecated = serializers.BooleanField()

    def _get_namespace(self, obj):
        raise NotImplementedError

    def get_namespace(self, obj):
        namespace = self._get_namespace(obj)
        return NamespaceSummarySerializer(namespace).data


class CollectionListSerializer(_CollectionSerializer):
    def _get_namespace(self, obj):
        name = obj['namespace']
        return self.context['namespaces'].get(name, None)


class CollectionDetailSerializer(_CollectionSerializer):
    latest_version = CollectionVersionDetailSerializer(source='*')
    all_versions = serializers.SerializerMethodField()

    def _get_namespace(self, obj):
        return self.context['namespace']

    def get_all_versions(self, obj):
        return [CollectionVersionSummarySerializer(version).data
                for version in self.context['all_versions']]
