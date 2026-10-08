import logging
import re

from django.db import transaction
from django.core import validators
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from rest_framework import fields

from pulpcore.plugin.serializers import IdentityField, ModelSerializer as PulpModelSerializer

from ansible_base.lib.serializers.mixins import CleanTextMixin
from ansible_base.lib.utils.validation import DEFAULT_NAME_FIELDS

from galaxy_ng.app import models
from galaxy_ng.app.tasks import dispatch_create_pulp_namespace_metadata
from galaxy_ng.app.access_control.fields import (
    GroupPermissionField,
    UserPermissionField,
    MyPermissionsField
)
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


class NamespaceLinkListSerializer(ScopedErrorListSerializer):
    """Bind matching stored NamespaceLink rows during many=True validation.

    DRF does not set child.instance when validating nested list writes, so
    CleanTextMixin's grandfather rule would treat every submitted link as new
    text. Match stored rows by (name, url) so an unchanged legacy link is not
    re-rejected on an unrelated namespace update (for example a description-only
    PUT that echoes the existing links).

    Matching both name and url is intentional whole-row grandfathering: if
    either field changes (including a URL-only edit on a link whose name is
    still legacy-invalid), child.instance stays unset and CleanTextMixin
    revalidates every submitted field.
    """

    def run_validation(self, *args, **kwargs):
        self._stored_links_index = self._build_stored_links_index()
        try:
            return super().run_validation(*args, **kwargs)
        finally:
            self._stored_links_index = None
            self.child.instance = None

    def run_child_validation(self, data):
        self.child.instance = None
        stored = getattr(self, '_stored_links_index', None) or {}
        if isinstance(data, dict):
            name = data.get('name')
            url = data.get('url')
            if isinstance(name, str) and isinstance(url, str):
                matches = stored.get((name, url))
                if matches:
                    self.child.instance = matches.pop()
        try:
            return super().run_child_validation(data)
        finally:
            self.child.instance = None

    def _build_stored_links_index(self):
        index = {}
        namespace = getattr(self.parent, 'instance', None)
        links = getattr(namespace, 'links', None) if namespace is not None else None
        if links is None:
            return index
        for link in links.all():
            index.setdefault((link.name, link.url), []).append(link)
        return index


class NamespaceLinkSerializer(CleanTextMixin, serializers.ModelSerializer):
    # Link captions are display labels ("Docs (EN)", "Q&A", "GitHub / Docs"), not
    # resource identifiers. Tier 1's strict allowlist rejects those characters;
    # demote `name` to Tier 2 so captions still block HTML/script/template/control
    # characters without rejecting legitimate punctuation.
    name_fields = DEFAULT_NAME_FIELDS - {'name'}

    # Using a CharField instead of a URLField so that we can add a custom error
    # message that includes the submitted URL
    url = serializers.CharField(
        max_length=256,
        allow_blank=False
    )

    class Meta:
        model = models.NamespaceLink
        fields = ('name', 'url')
        list_serializer_class = NamespaceLinkListSerializer
        scoped_error_name = 'links'

    # adds the URL to the error so the user can figure out which link the error
    # message is for
    def validate_url(self, url):
        v = validators.URLValidator(message=_("'%s' is not a valid url.") % url)
        v(url)
        return url


class NamespaceSerializer(CleanTextMixin, PulpModelSerializer):
    # Markdown profile content (platform-ui PageFormMarkdown). Exclude so
    # legitimate markdown (HTML-ish constructs, template-like fences, etc.) is
    # not rejected by Tier 2 free-text validation.
    excluded_fields = frozenset({'resources'})
    # Note: avatar_url is backed by the model's `_avatar_url` column (see
    # models.Namespace.avatar_url property), so CleanTextMixin's model-field
    # auto-discovery never matches it against this serializer's `avatar_url`
    # attrs key and it is not validated here.
    links = NamespaceLinkSerializer(many=True, required=False)
    groups = GroupPermissionField(required=False)
    users = UserPermissionField(required=False)
    related_fields = NamespaceRelatedFieldSerializer(source="*")
    avatar_url = fields.URLField(required=False, allow_blank=True)
    avatar_sha256 = serializers.SerializerMethodField()

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
            'users',
            'resources',
            'related_fields',
            'metadata_sha256',
            'avatar_sha256',
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

    def get_avatar_sha256(self, obj):
        if obj.last_created_pulp_metadata:
            return obj.last_created_pulp_metadata.avatar_sha256
        return None

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

        dispatch_create_pulp_namespace_metadata(instance, True)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        links = validated_data.pop('links', None)
        download_logo = False
        if "avatar_url" in validated_data:
            download_logo = True

        if links is not None:
            instance.set_links(links)

        instance = super().update(instance, validated_data)
        instance.save()
        dispatch_create_pulp_namespace_metadata(instance, download_logo)
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
            'users',
            'related_fields',
            'metadata_sha256',
            'avatar_sha256'
        )

        read_only_fields = ('name', )
