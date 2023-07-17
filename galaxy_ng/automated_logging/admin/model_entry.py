"""
Everything related to the admin interface of ModelEntry is located in here
"""

from django.contrib.admin import register
from django.shortcuts import redirect

from automated_logging.admin.model_event import ModelEventAdmin
from automated_logging.admin.base import ReadOnlyAdminMixin, ReadOnlyTabularInlineMixin
from automated_logging.models import ModelEntry, ModelEvent


class ModelEventInline(ReadOnlyTabularInlineMixin):
    """ inline for all attached events """

    model = ModelEvent

    def __init__(self, *args, **kwargs):
        super(ModelEventInline, self).__init__(*args, **kwargs)

        self.readonly_fields = [*self.readonly_fields, 'get_uuid', 'get_modifications']

    def get_uuid(self, instance):
        """ make the uuid small """
        return self.model_admin_url(instance, str(instance.id).split('-')[0])

    get_uuid.short_description = 'UUID'

    def get_modifications(self, instance):
        """ ModelEventAdmin already implements this functions, we just refer to it"""
        return ModelEventAdmin.get_modifications(self, instance)

    get_modifications.short_description = 'Modifications'

    fields = ('get_uuid', 'updated_at', 'user', 'get_modifications')

    ordering = ('-updated_at',)

    verbose_name = 'Event'
    verbose_name_plural = 'Events'


@register(ModelEntry)
class ModelEntryAdmin(ReadOnlyAdminMixin):
    """ admin page specification for ModelEntry """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.readonly_fields = [*self.readonly_fields, 'get_model', 'get_application']

    def changelist_view(self, request, **kwargs):
        """ instead of showing the changelist view redirect to the parent app_list"""
        return redirect('admin:app_list', self.model._meta.app_label)

    def has_module_permission(self, request):
        """ remove model entries from the index.html list """
        return False

    def get_model(self, instance):
        """ get the model mirror """
        return self.model_admin_url(instance.mirror)

    get_model.short_description = 'Model'

    def get_application(self, instance):
        """ get the application """
        return instance.mirror.application

    get_application.short_description = 'Application'

    fieldsets = (
        (
            'Information',
            {'fields': ('id', 'get_model', 'get_application', 'primary_key', 'value')},
        ),
    )

    inlines = [ModelEventInline]
