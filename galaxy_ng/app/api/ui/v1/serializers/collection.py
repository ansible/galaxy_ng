import logging

from pulp_ansible.app.models import (
    AnsibleDistribution,
    CollectionVersion,
)
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
import semantic_version

from .base import Serializer
from galaxy_ng.app.api.v3.serializers.namespace import NamespaceSummarySerializer
from galaxy_ng.app.models import Namespace

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


class RequestDistroMixin:
    """This provides _get_current_distro() to all serializers that inherit from it."""

    def _get_current_distro(self):
        """Get current distribution from request information."""
        request = self.context.get("request")
        try:
            # on URLS like _ui/v1/repo/rh-certified/namespace/name and
            # /api/automation-hub/_ui/v1/repo/community/
            # the distro_base_path can be parsed from the URL
            path = request.parser_context['kwargs']['distro_base_path']
        except KeyError:
            # this same serializer is used on /_ui/v1/collection-versions/
            # which can have the distro_base_path passed in as a query param
            # on the `?repository=` field
            path = request.query_params.get('repository')
        except AttributeError:
            # if there is no request, we are probably in a unit test
            return None

        if not path:
            # A bare /_ui/v1/collection-versions/ is not scoped to a single distro
            return None

        distro = AnsibleDistribution.objects.get(base_path=path)

        return distro


class CollectionMetadataSerializer(RequestDistroMixin, Serializer):
    dependencies = serializers.JSONField()
    contents = serializers.JSONField()

    # URLs
    documentation = serializers.CharField()
    homepage = serializers.CharField()
    issues = serializers.CharField()
    repository = serializers.CharField()

    description = serializers.CharField()
    authors = serializers.ListField(child=serializers.CharField())
    license = serializers.ListField(child=serializers.CharField())
    tags = serializers.SerializerMethodField()
    signatures = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_signatures(self, obj):
        """Returns signature info for each signature."""
        distro = self._get_current_distro()
        if not distro:
            signatures = obj.signatures.all()
        else:
            signatures = obj.signatures.filter(repositories=distro.repository)

        data = []
        for signature in signatures:
            sig = {}
            sig["signature"] = signature.data
            sig["pubkey_fingerprint"] = signature.pubkey_fingerprint
            sig["signing_service"] = getattr(signature.signing_service, "name", None)
            data.append(sig)
        return data

    @extend_schema_field(serializers.ListField)
    def get_tags(self, collection_version):
        # TODO(awcrosby): remove when galaxy_pulp no longer used in _ui
        if isinstance(collection_version, dict):
            return [tag['name'] for tag in collection_version['tags']]

        return [tag.name for tag in collection_version.tags.all()]


class CollectionVersionSignStateMixin(RequestDistroMixin):

    @extend_schema_field(serializers.CharField())
    def get_sign_state(self, obj):
        """Returns the state of the signature."""
        distro = self._get_current_distro()
        if not distro:
            signature_count = obj.signatures.count()
        else:
            signature_count = obj.signatures.filter(repositories=distro.repository).count()

        return "unsigned" if signature_count == 0 else "signed"


class CollectionVersionBaseSerializer(CollectionVersionSignStateMixin, Serializer):
    id = serializers.UUIDField(source='pk')
    namespace = serializers.CharField()
    name = serializers.CharField()
    version = serializers.CharField()
    requires_ansible = serializers.CharField()
    created_at = serializers.DateTimeField(source='pulp_created')
    metadata = serializers.SerializerMethodField()
    contents = serializers.ListField(child=ContentSerializer())
    sign_state = serializers.SerializerMethodField()

    @extend_schema_field(serializers.JSONField)
    def get_metadata(self, obj):
        return CollectionMetadataSerializer(obj, context=self.context).data


class CollectionVersionSerializer(CollectionVersionBaseSerializer):
    repository_list = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField)
    def get_repository_list(self, collection_version):
        """Repository list where content is in the latest RepositoryVersion."""

        # get all repos where content exists in a RepositoryVersion
        content = collection_version.content_ptr
        all_repos = content.repositories.all().distinct().exclude(name__endswith='-synclist')

        qs = CollectionVersion.objects.filter(pk=collection_version.pk)
        cv_in_repo_latest_version = []
        for repo in all_repos:
            if qs.filter(pk__in=repo.latest_version().content):
                cv_in_repo_latest_version.append(repo.name)
        return cv_in_repo_latest_version


class CollectionVersionDetailSerializer(CollectionVersionBaseSerializer):
    docs_blob = serializers.JSONField()


class CollectionVersionSummarySerializer(CollectionVersionSignStateMixin, Serializer):
    id = serializers.UUIDField(source='pk')
    version = serializers.CharField()
    created = serializers.CharField(source='pulp_created')
    sign_state = serializers.SerializerMethodField()


class _CollectionSerializer(Serializer):
    """ Serializer for pulp_ansible CollectionViewSet.
    Uses CollectionVersion object to serialize associated Collection data.
    """

    id = serializers.UUIDField(source='pk')
    namespace = serializers.SerializerMethodField()
    name = serializers.CharField()
    download_count = serializers.IntegerField(default=0)
    latest_version = serializers.SerializerMethodField()

    @extend_schema_field(NamespaceSummarySerializer)
    def get_namespace(self, obj):
        namespace = Namespace.objects.get(name=obj.namespace)
        return NamespaceSummarySerializer(namespace, context=self.context).data


class CollectionListSerializer(_CollectionSerializer):
    deprecated = serializers.BooleanField()
    sign_state = serializers.CharField()

    @extend_schema_field(CollectionVersionBaseSerializer)
    def get_latest_version(self, obj):
        return CollectionVersionBaseSerializer(obj, context=self.context).data


class CollectionDetailSerializer(_CollectionSerializer):
    all_versions = serializers.SerializerMethodField()
    sign_state = serializers.CharField()

    # TODO: rename field to "version_details" since with
    # "version" query param this won't always be the latest version
    @extend_schema_field(CollectionVersionDetailSerializer)
    def get_latest_version(self, obj):
        return CollectionVersionDetailSerializer(obj, context=self.context).data

    @extend_schema_field(CollectionVersionSummarySerializer(many=True))
    def get_all_versions(self, obj):
        path = self.context['request'].parser_context['kwargs']['distro_base_path']
        distro = AnsibleDistribution.objects.get(base_path=path)
        repository_version = distro.repository.latest_version()
        versions_in_repo = CollectionVersion.objects.filter(
            pk__in=repository_version.content,
            collection=obj.collection,
        ).only("content_ptr_id", "version")
        versions_in_repo = sorted(
            versions_in_repo, key=lambda obj: semantic_version.Version(obj.version), reverse=True
        )
        return CollectionVersionSummarySerializer(versions_in_repo, many=True).data
