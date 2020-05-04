import logging

from rest_framework import serializers

from pulp_ansible.app import models as pulp_ansible_models

from galaxy_ng.app import models

log = logging.getLogger(__name__)


class SyncListCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = pulp_ansible_models.Collection
        fields = ["namespace", "name"]


class SyncListSerializer(serializers.ModelSerializer):
    namespaces = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=models.Namespace.objects.all()
    )

    collections = SyncListCollectionSerializer(many=True)

    groups = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=models.Group.objects.all()
    )

    users = serializers.SlugRelatedField(
        many=True, slug_field="username", queryset=models.User.objects.all()
    )

    def create(self, validated_data):
        collections_data = validated_data.pop("collections")

        namespaces_data = validated_data.pop("namespaces")

        users_data = validated_data.pop("users")
        groups_data = validated_data.pop("groups")

        instance = models.SyncList.objects.create(**validated_data)
        for collection_data in collections_data:
            instance.collections.add(pulp_ansible_models.Collection.objects.get(**collection_data))

        for namespace_data in namespaces_data:

            instance.namespaces.add(namespace_data)

        instance.groups.set(groups_data)
        instance.users.set(users_data)

        return instance

    def update(self, instance, validated_data):
        collections_data = validated_data.get("collections")

        namespaces_data = validated_data.get("namespaces")

        users_data = validated_data.get("users")

        if users_data:
            instance.users.clear()
            instance.users.set(users_data)

        groups_data = validated_data.get("groups")
        if groups_data:
            instance.groups.clear()
            instance.groups.set(groups_data)

        instance.policy = validated_data.get("policy", instance.policy)

        instance.name = validated_data.get("name", instance.name)

        new_collections = []
        for collection_data in collections_data:
            new_collections.append(pulp_ansible_models.Collection.objects.get(**collection_data))

        instance.collections.set(new_collections)

        new_namespaces = []
        for namespace_data in namespaces_data:
            new_namespaces.append(namespace_data)

        instance.namespaces.set(new_namespaces)

        instance.save()

        return instance

    class Meta:
        model = models.SyncList
        fields = [
            "id",
            "name",
            "policy",
            "repository",
            "collections",
            "namespaces",
            "users",
            "groups",
        ]
