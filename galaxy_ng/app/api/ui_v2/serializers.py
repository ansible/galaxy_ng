# from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth import password_validation
from django.utils.translation import gettext_lazy as _

from galaxy_ng.app.api.ui.serializers import UserSerializer as UserSerializerV1
from galaxy_ng.app.models.auth import User
from galaxy_ng.app.models.auth import Group
from galaxy_ng.app.models.organization import Organization
from galaxy_ng.app.models.organization import Team


class UserSerializer(UserSerializerV1):
    resource = serializers.SerializerMethodField()
    teams = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()

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
            'auth_provider',
            'resource',
        ]

        extra_kwargs = {
            'resource': {'read_only': True},
            'date_joined': {'read_only': True},
            'password': {'write_only': True, 'allow_blank': True, 'required': False},
            'email': {'allow_blank': True, 'required': False}
        }

    def save(self, *args, **kwargs):
        print(f'SAVE: args:{args} kwargs:{kwargs}')
        super().save(*args, **kwargs)

    def validate_password(self, password):
        if password:
            password_validation.validate_password(password)
            return password

    def validate_groups(self, groups):
        request_user = self.context['request'].user

        group_set = set(groups)
        instance_group_set = set()
        if self.instance:
            instance_group_set = set(list(self.instance.groups.all()))

        group_difference = instance_group_set.symmetric_difference(group_set)

        if not request_user.has_perm('galaxy.change_group'):
            authed_user_groups = request_user.groups.all()
            for g in group_difference:
                if not authed_user_groups.filter(pk=g.id).exists():
                    raise ValidationError(detail={
                        "groups": _("'galaxy.change_group' permission is required to change"
                                    " a users group that the requesting user is not in.")
                    })

        return groups

    def validate_teams(self, teams):
        return teams

    def validate_organizations(self, organizations):
        return organizations

    def get_resource(self, obj):
        return obj.resource.summary_fields()

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

    def create(self, data):

        print(f'## SERIALIZER_CREATE: data:{data}')

        instance = super().create(data)
        instance = self._set_password(instance, data, updating=False)
        instance.save()
        return instance

    def update(self, instance, data):
        if instance.is_superuser and not self.context['request'].user.is_superuser:
            raise ValidationError(detail={
                "username": _("You do not have permissions to modify super users.")
            })

        instance = self._set_password(instance, data, updating=True)

        return super().update(instance, data)

    def _set_password(self, instance, data, updating):
        # password doesn't get set the same as other data, so delete it
        # before the serializer saves
        password = data.pop('password', None)
        if password:
            if updating:
                user = self.context['request'].user
                if not user.is_superuser and user.pk != instance.pk:
                    raise ValidationError(detail={
                        "password": _("Must be a super user to change another user's password.")
                    })

            instance.set_password(password)

        return instance

    def to_internal_value(self, data):
        groups = data.get('groups')
        if groups:
            group_ids = []
            for group in groups:
                group_filter = {}
                for field in group:
                    if field in ('id', 'name'):
                        group_filter[field] = group[field]
                try:
                    group = Group.objects.get(**group_filter)
                    group_ids.append(group.id)
                except Group.DoesNotExist:
                    raise ValidationError(detail={
                        'groups': _('Group name=%(name)s, id=%(id)s does not exist') % {
                            'name': group.get('name'), 'id': group.get('id')}
                    })
                except ValueError:
                    raise ValidationError(detail={'group': _('Invalid group name or ID')})
            data['groups'] = group_ids

        teams = data.get('teams')
        if teams:
            team_ids = []
            for team in teams:
                team_filter = {}
                for field in team:
                    if field in ('id', 'name'):
                        team_filter[field] = team[field]
                try:
                    team = Team.objects.get(**team_filter)
                    team_ids.append(team.id)
                except Team.DoesNotExist:
                    raise ValidationError(detail={
                        'teams': _('Team name=%(name)s, id=%(id)s does not exist') % {
                            'team': team.get('name'), 'id': team.get('id')}
                    })
                except ValueError:
                    raise ValidationError(detail={'teams': _('Invalid team name or ID')})
            data['teams'] = team_ids

        orgs = data.get('organizations')
        if orgs:
            org_ids = []
            for org in orgs:
                org_filter = {}
                for field in org:
                    if field in ('id', 'name'):
                        org_filter[field] = org[field]
                try:
                    org = Organization.objects.get(**org_filter)
                    org_ids.append(org.id)
                except Organization.DoesNotExist:
                    raise ValidationError(detail={
                        'organizations': _('Org name=%(name)s, id=%(id)s does not exist') % {
                            'organization': org.get('name'), 'id': org.get('id')}
                    })
                except ValueError:
                    raise ValidationError(detail={'organizations': _('Invalid org name or ID')})
            data['organizations'] = org_ids

        # return super().to_internal_value(data)
        return data


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
