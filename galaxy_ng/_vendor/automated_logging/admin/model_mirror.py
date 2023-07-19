"""
Everything related to the admin interface of ModelMirror is located in here
"""
from django.contrib.admin import register
from django.shortcuts import redirect

from automated_logging.admin.base import ReadOnlyAdminMixin, ReadOnlyTabularInlineMixin
from automated_logging.models import ModelMirror, ModelField


class ModelFieldInline(ReadOnlyTabularInlineMixin):
    """ list all recorded fields """

    model = ModelField

    fields = ['name', 'type']

    verbose_name = 'Recorded Field'
    verbose_name_plural = 'Recorded Fields'


@register(ModelMirror)
class ModelMirrorAdmin(ReadOnlyAdminMixin):
    """ admin page specification for ModelMirror """

    def has_module_permission(self, request):
        """ prevents this from showing up index.html """
        return False

    def changelist_view(self, request, **kwargs):
        """ instead of showing the changelist view redirect to the parent app_list"""
        return redirect('admin:app_list', self.model._meta.app_label)

    date_hierarchy = 'updated_at'
    ordering = ('-updated_at',)

    fieldsets = (('Information', {'fields': ('id', 'application', 'name')},),)

    inlines = [ModelFieldInline]
