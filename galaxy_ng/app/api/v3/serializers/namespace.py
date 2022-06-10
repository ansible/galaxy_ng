import logging
import re

from django.db import transaction
from django.core import validators
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from pulpcore.plugin.serializers import IdentityField

from galaxy_ng.app import models
from galaxy_ng.app.access_control.fields import GroupPermissionField, MyPermissionsField
from galaxy_ng.app.api.base import RelatedFieldsBaseSerializer

log = logging.getLogger(__name__)


class NamespaceRelatedFieldSerializer(RelatedFieldsBaseSerializer):
    my_permissions = MyPermissionsField(source="*", read_only=True)


class ScopedErrorListSerializer(serializers.ListSerializer):
    # Updates the list serializer to return error messages as "<childname>__<fieldname>"
    # This is to accomodate for cases where a serializer has to validate a list of
    # sub serializers. Normally error messages will just return the child's field name
    # but this can lead to situations where it's not clear if an error is originating
    # from the child or parent serializer when they share field names.
    def run_validation(self, *args, **kwargs):
        scoped_err_name = self.child.Meta.scoped_error_name

        try:
            return super().run_validation(*args, **kwargs)
        except (ValidationError) as exc:
            new_detail = []
            # loop through list of errors
            for err in exc.detail:
                new_err = {}
                # loop for fields in error
                for field in err:
                    new_err["{}__{}".format(scoped_err_name, field)] = err[field]

                new_detail.append(new_err)

            exc.detail = new_detail
            raise


class NamespaceLinkSerializer(serializers.ModelSerializer):
    # Using a CharField instead of a URLField so that we can add a custom error
    # message that includes the submitted URL
    url = serializers.CharField(
        max_length=256,
        allow_blank=False
    )

    class Meta:
        model = models.NamespaceLink
        fields = ('name', 'url')
        list_serializer_class = ScopedErrorListSerializer
        scoped_error_name = 'links'

    # adds the URL to the error so the user can figure out which link the error
    # message is for
    def validate_url(self, url):
        v = validators.URLValidator(message=_("'%s' is not a valid url.") % url)
        v(url)
        return url


class NamespaceSerializer(serializers.ModelSerializer):
    links = NamespaceLinkSerializer(many=True, required=False)
    groups = GroupPermissionField()
    related_fields = NamespaceRelatedFieldSerializer(source="*")

    # Add a pulp href to namespaces so that it can be referenced in the roles API.
    pulp_href = IdentityField(view_name="pulp_ansible/namespaces-detail", lookup_field="pk")

    class Meta:
        model = models.Namespace
        fields = (
            'pulp_href',
            'id',
            'name',
            'company',
            'email',
            'avatar_url',
            'description',
            'links',
            'groups',
            'resources',
            'related_fields',
        )

    # replace with a NamespaceNameSerializer and validate_name() ?
    def validate_name(self, name):
        if not name:
            raise ValidationError(detail={
                'name': _("Attribute 'name' is required")})
        if not re.match(r'^[a-z0-9_]+$', name):
            raise ValidationError(detail={
                'name': _('Name can only contain lower case letters, underscores and numbers')})
        if len(name) <= 2:
            raise ValidationError(detail={
                'name': _('Name must be longer than 2 characters')})
        if name.startswith('_'):
            raise ValidationError(detail={
                'name': _("Name cannot begin with '_'")})
        return name

    @transaction.atomic
    def create(self, validated_data):
        links_data = validated_data.pop('links', [])

        instance = models.Namespace.objects.create(**validated_data)

        # create NamespaceLink objects if needed
        new_links = []
        for link_data in links_data:
            link_data["namespace"] = instance
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
            'pulp_href',
            'id',
            'name',
            'company',
            'email',
            'avatar_url',
            'description',
            'groups',
            'related_fields',
        )

        read_only_fields = ('name', )
