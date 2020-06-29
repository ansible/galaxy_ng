import logging

from django.db import transaction
from django.db.utils import IntegrityError


from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from pulp_ansible.app.models import Collection
from pulp_ansible.app.models import AnsibleRepository, AnsibleDistribution

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app import models


log = logging.getLogger(__name__)


class SyncListCollectionSummarySerializer(serializers.Serializer):
    namespace = serializers.CharField(max_length=64)
    name = serializers.CharField(max_length=64)


class SyncListSerializer(serializers.ModelSerializer):
    namespaces = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=models.Namespace.objects.all()
    )

    collections = SyncListCollectionSummarySerializer(many=True)

    groups = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=models.Group.objects.all()
    )

    users = serializers.SlugRelatedField(
        many=True, slug_field="username", queryset=models.User.objects.all()
    )

    def _sanitize_groups(self, group_names):
        """Ensure that the admin/pe group is in the list of groups"""
        # All synclists are co-owned by admin group
        groups = [auth_models.RH_PARTNER_ENGINEER_GROUP]

        # no groups specified, use the groups from the request
        # FIXME: Would it be better to provide this in the serializer context?
        #        That would decouple this from the request object.
        if not group_names:
            request = self.context.get('request', None)
            if request:
                groups += [group.name for group in request.user.groups.all()]

        for group_name in group_names:
            if group_name == auth_models.RH_PARTNER_ENGINEER_GROUP:
                continue
            group = auth_models.Group.objects.get(name=group_name)
            groups.append(group.name)

        return groups

    def _get_repository(self, repository_id):
        try:
            repository = AnsibleRepository.objects.get(pulp_id=repository_id)
            # TODO: validate there is a distro associatd?
            return repository
        except AnsibleRepository.DoesNotExist:
            errmsg = \
                'Repository "{pulp_id}" not found while creating synclist'
            raise ValidationError(
                errmsg.format(pulp_id=repository_id))

    def to_internal_value(self, data):
        groups = data.get('groups', [])
        data['groups'] = self._sanitize_groups(groups)

        repository_data = data.get('repository', None)
        if repository_data:
            data['repository'] = self._get_repository(repository_data)

        return super().to_internal_value(data)

    def _name_slug_from_group_names(self, groups_data):
        ngs = auth_models.Group.objects.filter(name__in=[x.name for x in groups_data])
        ngs = ngs.filter(name__ne=auth_models.RH_PARTNER_ENGINEER_GROUP)

        if not ngs.filter():
            # TODO: better error
            errmsg = 'No Group found while creating synclist'
            raise ValidationError(errmsg)

        # FIXME: further filter for group name scope?

        account_name = ngs.filter()[0].account_number()
        name_slug = f"{account_name}-synclist"

        return name_slug, account_name

    @transaction.atomic
    def _create_repository(self, name_slug, account_name):

        # lookup groups, to get a group name to use in naming the repository/distro
        try:
            description = f"Synclist repository for account {account_name}"

            repository, created = AnsibleRepository.objects.get_or_create(name=name_slug)
            repository.description = description
            repository.save()
        except IntegrityError as exc:
            raise ValidationError("AnsibleRepository %s already exists: %s" % (name_slug, exc))
        except Exception as exc:
            log.exception(exc)
            raise

        # Now the distro
        try:
            distribution, create = AnsibleDistribution.objects.get_or_create(
                name=name_slug,
                base_path=name_slug,
            )
            if create:
                distribution.repository = repository

            # distribution.save()
        except IntegrityError as exc:
            raise ValidationError("AnsibleDistribution %s already exists: %s" % (name_slug, exc))
        except Exception as exc:
            log.exception(exc)
            raise

        return repository

    @transaction.atomic
    def create(self, validated_data):
        collections_data = validated_data.pop("collections")

        namespaces_data = validated_data.pop("namespaces")
        users_data = validated_data.pop("users")
        groups_data = validated_data.pop("groups")

        repository = validated_data.pop("repository", None)

        name_slug, account_name = self._name_slug_from_group_names(groups_data)

        if not repository:
            repository = self._create_repository(name_slug, account_name)

        try:
            instance = models.SyncList.objects.create(repository=repository,
                                                      name=name_slug, **validated_data)
        except IntegrityError as exc:
            raise ValidationError("Synclist already exists: %s" % exc)

        collections = []
        for collection_data in collections_data:
            try:
                collections.append(Collection.objects.get(**collection_data))
            except Collection.DoesNotExist:
                errmsg = \
                    'Collection "{namespace}.{name}" not found while creating synclist {synclist}'
                raise ValidationError(
                    errmsg.format(namespace=collection_data["namespace"],
                                  name=collection_data["name"],
                                  synclist=instance.name))
        instance.collections.clear()
        instance.collections.set(collections)

        instance.namespaces.add(*namespaces_data)

        instance.groups.set(groups_data)
        instance.users.set(users_data)

        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        collections_data = validated_data.get("collections")

        users_data = validated_data.get("users")
        if users_data:
            instance.users.set(users_data)

        groups_data = validated_data.get("groups")
        if groups_data:
            instance.groups.set(groups_data)

        namespaces_data = validated_data.get("namespaces")
        if namespaces_data:
            instance.namespaces.set(namespaces_data)

        instance.policy = validated_data.get("policy", instance.policy)

        instance.name = validated_data.get("name", instance.name)

        new_collections = []
        for collection_data in collections_data:
            try:
                new_collections.append(Collection.objects.get(**collection_data))
            except Collection.DoesNotExist:
                errmsg = \
                    'Collection "{namespace}.{name}" not found while updating synclist {synclist}'
                raise ValidationError(
                    errmsg.format(namespace=collection_data["namespace"],
                                  name=collection_data["name"],
                                  synclist=instance.name))
        instance.collections.set(new_collections)

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

        read_only_fields = ('name', 'repository')
