import logging
import re

from django.db import transaction

from rest_framework.exceptions import ValidationError
from rest_framework import serializers


from galaxy_ng.app import models
from galaxy_ng.app.access_control.fields import GroupPermissionField

log = logging.getLogger(__name__)


class NamespaceLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NamespaceLink
        fields = ('name', 'url')


class NamespaceSerializer(serializers.ModelSerializer):
    links = NamespaceLinkSerializer(many=True, required=False)

    groups = GroupPermissionField()

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

    # replace with a NamespaceNameSerializer and validate_name() ?
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

    @transaction.atomic
    def create(self, validated_data):
        links_data = validated_data.pop('links', [])

        instance = models.Namespace.objects.create(**validated_data)

        # create NamespaceLink objects if needed
        new_links = []
        for link_data in links_data:
            ns_link, created = models.NamespaceLink.objects.get_or_create(**link_data)
            new_links.append(ns_link)

        instance.links.set(new_links)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        links = validated_data.pop('links', None)

        if links is not None:
            instance.set_links(links)

        instance = super().update(instance, validated_data)
        instance.save()
        return instance


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
            'groups',
        )

        read_only_fields = ('name', )
