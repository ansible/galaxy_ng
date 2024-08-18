# from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth import password_validation
from django.core.validators import EmailValidator
from django.utils.translation import gettext_lazy as _

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.models.auth import Group
from galaxy_ng.app.models.organization import Organization
from galaxy_ng.app.models.organization import Team


class UserDetailSerializer(serializers.ModelSerializer):
    resource = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    teams = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'groups',
            'teams',
            'organizations',
            'date_joined',
            'is_superuser',
            'resource',
        ]

    def get_resource(self, obj):
        return obj.resource.summary_fields()

    def get_groups(self, obj):
        groups = obj.groups.all()
        groups_serializer = GroupSerializer(groups, many=True)
        return groups_serializer.data

    def get_teams(self, obj):
        teams = Team.objects.filter(users=obj)
        teams_serializer = TeamSerializer(teams, many=True)
        return teams_serializer.data

    def get_organizations(self, obj):
        # FIXME - team membership doesn't imply this should also
        #         show the orgs from those teams ... right?
        orgs = Organization.objects.filter(users=obj)
        orgs_serializer = OrganizationSerializer(orgs, many=True)
        return orgs_serializer.data


class UserCreateUpdateSerializer(UserDetailSerializer):

    groups = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )

    teams = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )

    organizations = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'password',
            'first_name',
            'last_name',
            'email',
            'groups',
            'teams',
            'organizations',
            'date_joined',
            'is_superuser',
            'resource',
        ]

        extra_kwargs = {
            'id': {'read_only': True, 'required': True},
            'username': {'allow_blank': False, 'required': True},
            'resource': {'read_only': True},
            'date_joined': {'read_only': True},
            'password': {'write_only': True, 'allow_blank': True, 'required': False},
        }

    def is_valid(self, *args, **kwargs):
        return super().is_valid(*args, **kwargs)

    def to_internal_value(self, data):
        return super().to_internal_value(data)

    def validate_password(self, password):
        if password is not None:
            password_validation.validate_password(password)
            return password
        return password

    def create(self, validated_data):
        # Pop the groups data from the validated data
        groups_data = validated_data.pop('groups', None)
        teams_data = validated_data.pop('teams', None)
        orgs_data = validated_data.pop('organizations', None)

        # Create the user without the groups data
        user = User.objects.create_user(**validated_data)

        if groups_data:
            for group_dict in groups_data:
                group_filter = {}
                for field in group_dict.keys():
                    if field in ('id', 'name'):
                        group_filter[field] = group_dict[field]

                try:
                    group = Group.objects.get(**group_filter)
                    user.groups.add(group)
                except Group.DoesNotExist:
                    raise ValidationError(detail={
                        'groups': _('Group name=%(name)s, id=%(id)s does not exist') % {
                            'name': group_dict.get('name'), 'id': group_dict.get('id')}
                    })
                except ValueError:
                    raise ValidationError(detail={'group': _('Invalid group name or ID')})

        if teams_data:
            for team_dict in teams_data:
                team_filter = {}
                for field in team_dict.keys():
                    if field in ('id', 'name'):
                        team_filter[field] = team_dict[field]
                try:
                    team = Team.objects.get(**team_filter)
                    team.users.add(user)
                except Team.DoesNotExist:
                    raise ValidationError(detail={
                        'teams': _('Team name=%(name)s, id=%(id)s does not exist') % {
                            'name': team_dict.get('name'), 'id': team_dict.get('id')}
                    })
                except ValueError:
                    raise ValidationError(detail={'teams': _('Invalid team name or ID')})

        if orgs_data:
            for org_dict in orgs_data:
                org_filter = {}
                for field in org_dict.keys():
                    if field in ('id', 'name'):
                        org_filter[field] = org_dict[field]
                try:
                    org = Organization.objects.get(**org_filter)
                    org.users.add(user)
                except Organization.DoesNotExist:
                    raise ValidationError(detail={
                        'organizations': _('Org name=%(name)s, id=%(id)s does not exist') % {
                            'name': org_dict.get('name'), 'id': org_dict.get('id')}
                    })
                except ValueError:
                    raise ValidationError(detail={'organizations': _('Invalid org name or ID')})

        return user

    def update(self, instance, validated_data):
        # Update the rest of the fields as usual
        instance.username = validated_data.get('username', instance.username)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)

        # If password is provided, update it securely
        password = validated_data.get('password', None)
        if password:
            instance.set_password(password)

        instance.save()
        return instance


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            'id',
            'name',
        ]


class OrganizationSerializer(serializers.ModelSerializer):

    id = serializers.SerializerMethodField()
    resource = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id',
            'name',
            'resource',
        ]

    def get_id(self, obj):
        return obj.pk

    def get_resource(self, obj):
        return {
            'resource_type': obj.resource.content_type.name,
            'ansible_id': obj.resource.ansible_id,
        }


class TeamSerializer(serializers.ModelSerializer):

    group = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()
    resource = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            'id',
            'name',
            'group',
            'organization',
            'resource',
        ]

    def get_group(self, obj):
        return {
            'id': obj.group.id,
            'name': obj.group.name,
        }

    def get_organization(self, obj):
        return {
            'id': obj.organization.id,
            'name': obj.organization.name,
        }

    def get_resource(self, obj):
        return {
            'resource_type': obj.resource.content_type.name,
            'ansible_id': obj.resource.ansible_id,
        }
