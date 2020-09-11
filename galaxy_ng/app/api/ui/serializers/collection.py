import logging

from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    CollectionRemote,
    CollectionVersion,
)
from rest_framework import serializers
import semantic_version

from .base import Serializer
from galaxy_ng.app.api.v3.serializers.namespace import NamespaceSummarySerializer
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models.collectionsync import CollectionSyncTask

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
    created_at = serializers.DateTimeField(source='pulp_created')
    certification = serializers.ChoiceField(
        ['certified', 'not_certified', 'needs_review'],
        required=True
    )
    metadata = CollectionMetadataSerializer(source='*')
    contents = serializers.ListField(ContentSerializer())


class CollectionVersionSerializer(CollectionVersionBaseSerializer):
    repository_list = serializers.SerializerMethodField()

    def get_repository_list(self, collection_version):
        """Repository list where content is in the latest RepositoryVersion."""

        # get all repos where content exists in a RepositoryVersion
        content = collection_version.content_ptr
        all_repos = content.repositories.all().distinct().exclude(
            name__startswith='inbound-').exclude(name__endswith='-synclist')

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


class RepositoryCollectionVersionSummarySerializer(Serializer):
    version = serializers.CharField()
    created = serializers.CharField(source='pulp_created')


class _RepositoryCollectionSerializer(Serializer):
    id = serializers.UUIDField(source='pk')
    namespace = serializers.SerializerMethodField()
    name = serializers.CharField()
    download_count = serializers.IntegerField(default=0)
    latest_version = serializers.SerializerMethodField()
    deprecated = serializers.BooleanField()

    def get_namespace(self, obj):
        namespace = Namespace.objects.get(name=obj.namespace)
        return NamespaceSummarySerializer(namespace).data

    def _get_versions_in_repo(self, obj):
        repo_param = self.context['repository']
        distro = AnsibleDistribution.objects.get(base_path=repo_param)
        repository_version = distro.repository.latest_version()
        collection_versions = CollectionVersion.objects.filter(collection=obj)

        versions_in_repo = collection_versions.filter(pk__in=repository_version.content)
        versions_in_repo = sorted(
            versions_in_repo, key=lambda obj: semantic_version.Version(obj.version), reverse=True
        )
        return versions_in_repo

    def _get_latest_version(self, obj):
        versions_in_repo = self._get_versions_in_repo(obj)
        return next(iter(versions_in_repo), None)


class RepositoryCollectionListSerializer(_RepositoryCollectionSerializer):
    def get_latest_version(self, obj):
        version = self._get_latest_version(obj)
        return CollectionVersionBaseSerializer(version).data


class RepositoryCollectionDetailSerializer(_RepositoryCollectionSerializer):
    all_versions = serializers.SerializerMethodField()

    def get_all_versions(self, obj):
        versions_in_repo = self._get_versions_in_repo(obj)
        return RepositoryCollectionVersionSummarySerializer(versions_in_repo, many=True).data

    def get_latest_version(self, obj):
        version = self._get_latest_version(obj)
        return CollectionVersionDetailSerializer(version).data


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

    def get_last_sync_task(self, obj):
        sync_task = CollectionSyncTask.objects.filter(repository=obj).last()

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


class CollectionRemoteSerializer(serializers.ModelSerializer):
    last_sync_task = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='pulp_created')
    updated_at = serializers.DateTimeField(source='pulp_last_updated')
    repositories = serializers.SerializerMethodField()

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
            'last_sync_task',
            'repositories',
        )
        extra_kwargs = {
            'name': {'read_only': True},
            'token': {'write_only': True},
        }

    def get_repositories(self, obj):
        return [
            AnsibleRepositorySerializer(repo).data
            for repo in obj.repository_set.all()
        ]

    def get_last_sync_task(self, obj):
        """Gets last_sync_task from Pulp using remote->repository relation"""

        sync_task = CollectionSyncTask.objects.filter(
            repository=obj.repository_set.order_by('-pulp_last_updated').first()
        ).first()

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
