from rest_framework import serializers

from ansible_base.lib.serializers.mixins import CleanTextMixin


class FakeModel:
    """
    Stand-in for Meta.model on plain (non-ModelSerializer) serializers.

    Only satisfies `_meta.app_label` / `_meta.object_name`, the two attributes
    CleanTextMixin's audit-log message reads -- it's never introspected for
    real fields, since PlainSerializerCleanTextMixin overrides field discovery
    to use the serializer's own declared CharFields instead.
    """

    def __init__(self, object_name):
        self._meta = type('Meta', (), {'app_label': 'galaxy', 'object_name': object_name})


class PlainSerializerCleanTextMixin(CleanTextMixin):
    """
    CleanTextMixin for plain `serializers.Serializer` subclasses with no
    backing Django model.

    CleanTextMixin discovers which fields to validate via
    `Meta.model._meta.get_fields()`. Serializers like LegacySyncSerializer
    represent one-off actions dispatched to Celery tasks, not a persisted,
    editable resource -- there's no single Django model whose fields map 1:1
    to what's submitted, so `Meta.model` doesn't exist here.

    This overrides ONLY field discovery: instead of introspecting a model, it
    treats the serializer's own declared CharFields as the text fields to
    validate. Everything else -- Tier 1/Tier 2 dispatch, name_fields /
    excluded_fields, audit logging, the ENHANCED_INPUT_VALIDATION_ENABLED
    enforcement gate -- is reused unchanged from CleanTextMixin. `Meta.model`
    must still be set (to a `FakeModel` instance) so the audit-log message in
    `_log_validation_failure` can resolve a resource type label.
    """

    def _classify_fields(self, model):
        # Known gap: unlike the parent's model-side get_internal_type() check --
        # which deliberately excludes format-constrained subclasses like SlugField
        # and GenericIPAddressField because they override get_internal_type() to
        # report their own type -- isinstance() here can't make that distinction.
        # DRF's SlugField/IPAddressField/RegexField/FilePathField are all
        # isinstance-subclasses of CharField with no equivalent "I'm not really
        # free text" signal to check, so they'd be swept into Tier 1/Tier 2
        # validation if ever declared on one of these serializers.
        #
        # Not fixed here because it doesn't apply to any current field: every
        # field on LegacySyncSerializer/LegacyImportSerializer/
        # LegacyRoleUpdateSerializer/LegacyRoleRepositoryUpdateSerializer is a
        # plain CharField. Excluding it properly would mean hand-maintaining a
        # list of DRF field classes (there's no field-level flag to introspect
        # the way there is on the Django model side), which is speculative
        # complexity for a field type that doesn't exist anywhere this mixin is
        # used. These are also the only write-accepting plain Serializers in the
        # whole Hub codebase with no backing model -- v1 is a frozen legacy
        # compatibility surface, so new fields of this shape here are unlikely.
        # If a SlugField/IPAddressField-like field is ever added here, or this
        # mixin gets reused elsewhere, revisit this check then.
        text_fields = [
            name for name, field in self.fields.items()
            if isinstance(field, serializers.CharField)
        ]
        return text_fields, []  # no JSONFields on these plain serializers
