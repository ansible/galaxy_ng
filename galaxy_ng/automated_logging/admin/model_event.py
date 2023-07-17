"""
Everything related to the admin interface of ModelEvent is located in here
"""

from django.contrib.admin import register, RelatedOnlyFieldListFilter
from django.utils.html import format_html

from automated_logging.admin.base import ReadOnlyTabularInlineMixin, ReadOnlyAdminMixin
from automated_logging.helpers import Operation
from automated_logging.models import (
    ModelValueModification,
    ModelRelationshipModification,
    ModelEvent,
)


class ModelValueModificationInline(ReadOnlyTabularInlineMixin):
    """ inline for all modifications """

    model = ModelValueModification

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.readonly_fields = [*self.readonly_fields, 'get_uuid', 'get_field']

    def get_uuid(self, instance):
        """ make the uuid small """
        return str(instance.id).split('-')[0]

    get_uuid.short_description = 'UUID'

    def get_field(self, instance):
        """ show the field name """
        return instance.field.name

    get_field.short_description = 'Field'

    fields = ('get_uuid', 'operation', 'get_field', 'previous', 'current')
    can_delete = False

    verbose_name = 'Modification'
    verbose_name_plural = 'Modifications'


class ModelRelationshipModificationInline(ReadOnlyTabularInlineMixin):
    """ inline for all relationship modifications """

    model = ModelRelationshipModification

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.readonly_fields = [*self.readonly_fields, 'get_uuid', 'get_field']

    def get_uuid(self, instance):
        """ make the uuid small """
        return str(instance.id).split('-')[0]

    get_uuid.short_description = 'UUID'

    def get_field(self, instance):
        """ show the field name """
        return instance.field.name

    get_field.short_description = 'Field'

    fields = ('get_uuid', 'operation', 'get_field', 'entry')
    can_delete = False

    verbose_name = 'Relationship'
    verbose_name_plural = 'Relationships'


@register(ModelEvent)
class ModelEventAdmin(ReadOnlyAdminMixin):
    """ admin page specification for ModelEvent """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.readonly_fields = [
            *self.readonly_fields,
            'get_application',
            'get_user',
            'get_model_link',
        ]

    def get_modifications(self, instance):
        """
        Modifications in short form, are colored for better readability.

        Colors taken from
        https://github.com/django/django/tree/master/django/contrib/admin/static/admin/img
        """
        colors = {
            Operation.CREATE: '#70bf2b',
            Operation.MODIFY: '#efb80b',
            Operation.DELETE: '#dd4646',
        }
        return format_html(
            ', '.join(
                [
                    *[
                        f'<span style="color: {colors[Operation(m.operation)]};">'
                        f'{m.short()}'
                        f'</span>'
                        for m in instance.modifications.all()
                    ],
                    *[
                        f'<span style="color: {colors[Operation(r.operation)]};">'
                        f'{r.medium()[0]}'
                        f'</span>[{r.medium()[1]}]'
                        for r in instance.relationships.all()
                    ],
                ],
            )
        )

    get_modifications.short_description = 'Modifications'

    def get_model(self, instance):
        """
        get the model
        TODO: consider splitting this up to model/pk/value
        """
        return instance.entry.short()

    get_model.short_description = 'Model'

    def get_model_link(self, instance):
        """ get the model with a link to the entry """
        return self.model_admin_url(instance.entry)

    get_model_link.short_description = 'Model'

    def get_application(self, instance):
        """
        helper to get the application from the child ModelMirror
        :param instance:
        :return:
        """
        return instance.entry.mirror.application

    get_application.short_description = 'Application'

    def get_id(self, instance):
        """ shorten the id to the first 8 digits """
        return str(instance.id).split('-')[0]

    get_id.short_description = 'UUID'

    def get_user(self, instance):
        """ return the user with a link """
        return self.model_admin_url(instance.user) if instance.user else None

    get_user.short_description = 'User'

    list_display = (
        'get_id',
        'updated_at',
        'user',
        'get_application',
        'get_model',
        'get_modifications',
    )

    list_filter = (
        'updated_at',
        ('user', RelatedOnlyFieldListFilter),
        ('entry__mirror__application', RelatedOnlyFieldListFilter),
        ('entry__mirror', RelatedOnlyFieldListFilter),
    )

    date_hierarchy = 'updated_at'
    ordering = ('-updated_at',)

    fieldsets = (
        (
            'Information',
            {
                'fields': (
                    'id',
                    'get_user',
                    'updated_at',
                    'get_application',
                    'get_model_link',
                )
            },
        ),
        ('Introspection', {'fields': ('performance', 'snapshot')}),
    )
    inlines = [ModelValueModificationInline, ModelRelationshipModificationInline]

    show_change_link = True
