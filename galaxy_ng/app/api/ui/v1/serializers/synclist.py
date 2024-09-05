import logging

from django.conf import settings
from django.db import transaction
from django.db.utils import IntegrityError
from django.utils.translation import gettext_lazy as _
from pulp_ansible.app.models import AnsibleRepository, Collection
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from galaxy_ng.app import models
from galaxy_ng.app.access_control.fields import GroupPermissionField

log = logging.getLogger(__name__)

default_repo_name = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH


class SyncListCollectionSummarySerializer(serializers.Serializer):
    namespace = serializers.CharField(max_length=64)
    name = serializers.CharField(max_length=64)


class SyncListSerializer(serializers.ModelSerializer):
    namespaces = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=models.Namespace.objects.all()
    )

    collections = SyncListCollectionSummarySerializer(many=True)

    groups = GroupPermissionField()

    def _get_repository(self, repository_id):
        try:
            repository = AnsibleRepository.objects.get(pulp_id=repository_id)
            return repository
        except AnsibleRepository.DoesNotExist:
            errmsg = _('Repository "{pulp_id}" not found while creating synclist')
            raise ValidationError(errmsg.format(pulp_id=repository_id))

    def to_internal_value(self, data):
        upstream_repository_data = data.get("upstream_repository", None)
        if upstream_repository_data:
            data["upstream_repository"] = self._get_repository(upstream_repository_data)
        else:
            # If not specified, use the default upstream repo
            data["upstream_repository"] = AnsibleRepository.objects.get(name=default_repo_name)
        return super().to_internal_value(data)

    @transaction.atomic
    def create(self, validated_data):
        collections_data = validated_data.pop("collections")
        namespaces_data = validated_data.pop("namespaces")

        # Match repository to upstream_repository
        # TODO: remove after SyncList no longer has FK to repositories
        repository = validated_data.pop("upstream_repository")

        try:
            instance = models.SyncList.objects.create(
                repository=repository,
                **validated_data
            )
        except IntegrityError as exc:
            raise ValidationError(_("Synclist already exists: %s") % exc)

        collections = []
        for collection_data in collections_data:
            try:
                collections.append(Collection.objects.get(**collection_data))
            except Collection.DoesNotExist:
                errmsg = (
                    _('Collection "{namespace}.{name}" not found '
                      'while creating synclist {synclist}')
                )
                raise ValidationError(
                    errmsg.format(
                        namespace=collection_data["namespace"],
                        name=collection_data["name"],
                        synclist=instance.name,
                    )
                )
        instance.collections.clear()
        instance.collections.set(collections)

        instance.namespaces.add(*namespaces_data)

        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        collections_data = validated_data.get("collections", [])

        groups_data = validated_data.get("groups")
        if groups_data:
            instance.groups = groups_data

        namespaces_data = validated_data.get("namespaces")
        if namespaces_data is not None:
            instance.namespaces.set(namespaces_data)

        instance.policy = validated_data.get("policy", instance.policy)

        instance.name = validated_data.get("name", instance.name)

        new_collections = []
        for collection_data in collections_data:
            try:
                new_collections.append(Collection.objects.get(**collection_data))
            except Collection.DoesNotExist:
                errmsg = (
                    _('Collection "{namespace}.{name}" not found '
                      'while updating synclist {synclist}')
                )
                raise ValidationError(
                    errmsg.format(
                        namespace=collection_data["namespace"],
                        name=collection_data["name"],
                        synclist=instance.name,
                    )
                )
        instance.collections.set(new_collections)

        instance.save()

        return instance

    class Meta:
        model = models.SyncList
        fields = [
            "id",
            "name",
            "policy",
            "upstream_repository",
            "repository",
            "distribution",
            "collections",
            "namespaces",
            "groups",
        ]

        read_only_fields = ("repository", )
