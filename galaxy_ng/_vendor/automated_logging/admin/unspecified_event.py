"""
Everything related to the admin interface of UnspecifiedEvent is located in here
"""
from django.contrib.admin import register, RelatedOnlyFieldListFilter

from automated_logging.admin.base import ReadOnlyAdminMixin, ReadOnlyTabularInlineMixin
from automated_logging.models import UnspecifiedEvent


@register(UnspecifiedEvent)
class UnspecifiedEventAdmin(ReadOnlyAdminMixin):
    """ admin page specification for the UnspecifiedEvent """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_id(self, instance):
        """ shorten the id to the first 8 digits """
        return str(instance.id).split('-')[0]

    get_id.short_description = 'UUID'

    list_display = ('get_id', 'updated_at', 'level', 'message')

    date_hierarchy = 'updated_at'
    ordering = ('-updated_at',)

    list_filter = ('updated_at',)

    fieldsets = (
        (
            'Information',
            {'fields': ('id', 'updated_at', 'application', 'level', 'message')},
        ),
        ('Location', {'fields': ('file', 'line')}),
    )
