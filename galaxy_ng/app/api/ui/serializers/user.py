from django.conf import settings
from django.contrib.auth import password_validation
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.constants import PERMISSIONS


class GroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = auth_models.Group
        fields = (
            'id',
            'name'
        )


class UserSerializer(serializers.ModelSerializer):
    auth_provider = serializers.SerializerMethodField()

    class Meta:
        model = auth_models.User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'groups',
            'password',
            'date_joined',
            'is_superuser',
            'auth_provider',
        )
        extra_kwargs = {
            'date_joined': {'read_only': True},
            'password': {'write_only': True, 'allow_blank': True, 'required': False}
        }

    def get_auth_provider(self, user):
        if hasattr(user, 'social_auth') and user.social_auth.all():
            providers = []
            for social in user.social_auth.all():
                providers.append(social.provider)
            return providers

        return ['django']

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

    def validate_is_superuser(self, data):
        request_user = self.context['request'].user

        # If the user is not a super user
        if not request_user.is_superuser:
            if self.instance:
                # Check if is_superuser is being modified, reject the request
                if self.instance.is_superuser != data:
                    raise ValidationError(detail={
                        "is_superuser": _("Must be a super user to grant super user permissions.")
                    })
            else:
                # if a new user is being created, reject the request if it is a super user
                if data:
                    raise ValidationError(detail={
                        "is_superuser": _("Must be a super user to grant super user permissions.")
                    })

        return data

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

    def create(self, data):
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

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['groups'] = GroupSerializer(instance.groups.all(), many=True).data
        return representation

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
                    group = auth_models.Group.objects.get(**group_filter)
                    group_ids.append(group.id)
                except auth_models.Group.DoesNotExist:
                    raise ValidationError(detail={
                        'groups': _('Group name=%(name)s, id=%(id)s does not exist') % {
                            'name': group.get('name'), 'id': group.get('id')}
                    })
                except ValueError:
                    raise ValidationError(detail={'group': _('Invalid group name or ID')})
            data['groups'] = group_ids
        return super().to_internal_value(data)


class CurrentUserSerializer(UserSerializer):
    model_permissions = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = auth_models.User
        fields = UserSerializer.Meta.fields + ('model_permissions', 'is_anonymous',)
        extra_kwargs = dict(
            groups={'read_only': True},
            **UserSerializer.Meta.extra_kwargs
        )

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_model_permissions(self, obj):
        permissions = {}
        for i, j in PERMISSIONS.items():
            permissions[i] = j
            permissions[i]["has_model_permission"] = obj.has_perm(i)
        if settings.get("SOCIAL_AUTH_KEYCLOAK_KEY"):
            permissions["galaxy.delete_user"]['has_model_permission'] = False
            permissions["galaxy.change_user"]['has_model_permission'] = False
            permissions["galaxy.add_user"]['has_model_permission'] = False
            permissions["galaxy.add_group"]['has_model_permission'] = False
            permissions["galaxy.delete_group"]['has_model_permission'] = False

        return permissions
