import re

from django.db import transaction

from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer, SlugRelatedField

from galaxy_ng.app import models
from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.auth import auth


class NamespaceLinkSerializer(ModelSerializer):
    class Meta:
        model = models.NamespaceLink
        fields = ('name', 'url')


class NamespaceSerializer(ModelSerializer):
    links = NamespaceLinkSerializer(many=True, required=False, read_only=True)
    groups = SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=auth_models.Group.objects.all()
    )

    class Meta:
        model = models.Namespace
        fields = (
            'id',
            'name',
            'company',
            'email',
            'avatar_url',
            'description',
            'links',
            'groups',
            'resources'
        )

    def validate_name(self, name):
        if not name:
            raise ValidationError(detail={
                'name': "Attribute 'name' is required"})
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            raise ValidationError(detail={
                'name': 'Name can only contain [A-Za-z0-9_]'})
        if len(name) <= 2:
            raise ValidationError(detail={
                'name': 'Name must be longer than 2 characters'})
        if name.startswith('_'):
            raise ValidationError(detail={
                'name': "Name cannot begin with '_'"})
        return name

    def to_internal_value(self, data):
        groups = data.get('groups')
        if groups:
            data['groups'] = self._sanitize_accounts(groups)
        return super().to_internal_value(data)

    def _sanitize_accounts(self, accounts):
        sanitized_groups = [auth_models.RH_PARTNER_ENGINEER_GROUP]
        for account in accounts:
            if account == auth_models.RH_PARTNER_ENGINEER_GROUP:
                continue
            if not account.isdigit():
                raise ValidationError(detail={
                    'groups': 'Provided identifications are not numbers'})
            group, _ = auth_models.Group.objects.get_or_create_identity(
                auth.RH_ACCOUNT_SCOPE, account)
            sanitized_groups.append(group.name)
        return sanitized_groups

    @transaction.atomic
    def update(self, instance, validated_data):
        links = validated_data.pop('links', None)

        instance = super().update(instance, validated_data)

        if links is not None:
            instance.set_links(links)

        return instance


class NamespaceUpdateSerializer(NamespaceSerializer):
    """NamespaceSerializer but read_only 'name'."""

    class Meta:
        model = models.Namespace
        fields = (
            'id',
            'name',
            'company',
            'email',
            'avatar_url',
            'description',
            'links',
            'groups',
            'resources'
        )

        read_only_fields = ('name', )


class NamespaceSummarySerializer(NamespaceSerializer):
    """NamespaceSerializer but without 'links' or 'resources'.

    For use in _ui/collection detail views."""

    class Meta:
        model = models.Namespace
        fields = (
            'id',
            'name',
            'company',
            'email',
            'avatar_url',
            'description',
        )

        read_only_fields = ('name', )
