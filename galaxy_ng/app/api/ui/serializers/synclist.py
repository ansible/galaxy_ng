import logging

from django.conf import settings
from django.db import transaction
from django.db.utils import IntegrityError


from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from pulp_ansible.app.models import Collection
from pulp_ansible.app.models import AnsibleRepository, AnsibleDistribution

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app import models


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

    groups = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=models.Group.objects.all()
    )

    users = serializers.SlugRelatedField(
        many=True, slug_field="username", queryset=models.User.objects.all()
    )

    def _sanitize_users(self, user_names):
        users = []
        if not user_names:
            request = self.context.get('request', None)
            if request:
                users.append(request.user)

        for user_name in user_names:
            user = auth_models.User.objects.get(username=user_name)
            users.append(user.username)

        return users

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

        users = data.get('users', [])
        data['users'] = self._sanitize_users(users)

        repository_data = data.get('repository', None)
        if repository_data:
            data['repository'] = self._get_repository(repository_data)

        upstream_repository_data = data.get('upstrean_repository', None)
        if upstream_repository_data:
            data['upstream_repository'] = self._get_repository(upstream_repository_data)
        else:
            # If not specified, use the default upstream repo
            data['upstream_repository'] = \
                AnsibleRepository.objects.get(name=default_repo_name)
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
        name_slug = settings.GALAXY_API_SYNCLIST_NAME_FORMAT.format(account_name=account_name)

        return name_slug, account_name

    @transaction.atomic
    def _create_repository(self, name_slug, account_name):
        # lookup groups, to get a group name to use in naming the repository/distro
        try:
            description = f"Synclist repository for account {account_name}"

            repository, created = AnsibleRepository.objects.get_or_create(name=name_slug)
            repository.description = description
            repository.save()
            return repository
        except IntegrityError as exc:
            raise ValidationError("AnsibleRepository %s already exists: %s" % (name_slug, exc))
        except Exception as exc:
            log.exception(exc)
            raise

    def _update_distribution(self, name_slug, repository):
        # Now the distro
        try:
            distribution, create = AnsibleDistribution.objects.get_or_create(
                name=name_slug,
                base_path=name_slug,
            )
        except IntegrityError as exc:
            raise ValidationError("AnsibleDistribution %s already exists: %s" % (name_slug, exc))
        except Exception as exc:
            log.exception(exc)
            raise

        # Now update the Distribution to point to the new Repository
        distribution.repository = repository

        distribution.save()
        return distribution

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
        collections_data = validated_data.get("collections", [])

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

        # if collection goes from empty to having something in it,
        # then we also need to point the associated distro to the synclist repo
        if instance.collections.all() and instance.repository:
            log.debug('inst.coll is truthy, ponting distro at the per org repo %s',
                      instance.repository)
            self._update_distribution(instance.name, instance.repository)
        else:
            log.debug('inst.coll is falsey, pointing distro back at upstream repo %s',
                      instance.upstream_repository)
            # synclist is no longer including/excluding anything, so point back
            # at the default upstream repo
            self._update_distribution(instance.name, instance.upstream_repository)

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
            "collections",
            "namespaces",
            "users",
            "groups",
        ]

        read_only_fields = ('name', 'repository')
