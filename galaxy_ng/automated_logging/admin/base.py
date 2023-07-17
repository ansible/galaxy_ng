from django.contrib.admin.options import BaseModelAdmin, ModelAdmin, TabularInline
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.shortcuts import resolve_url
from django.utils.html import format_html
from django.utils.safestring import SafeText

from automated_logging.models import BaseModel


class MixinBase(BaseModelAdmin):
    """
    TabularInline and ModelAdmin readonly mixin have both the same methods and
    return the same, because of that fact we have a mixin base
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.readonly_fields = [f.name for f in self.model._meta.get_fields()]

    def get_actions(self, request):
        """ get_actions from ModelAdmin, but remove all write operations."""
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)

        return actions

    def has_add_permission(self, request, instance=None):
        """ no-one should have the ability to add something => r/o"""
        return False

    def has_delete_permission(self, request, instance=None):
        """ no-one should have the ability to delete something => r/o """
        return False

    def has_change_permission(self, request, instance=None):
        """ no-one should have the ability to edit something => r/o """
        return False

    def save_model(self, request, instance, form, change):
        """ disable saving by doing nothing """
        pass

    def delete_model(self, request, instance):
        """ disable deleting by doing nothing """
        pass

    def save_related(self, request, form, formsets, change):
        """ we don't need to save related, because save_model does nothing """
        pass

    # helpers
    def model_admin_url(self, instance: BaseModel, name: str = None) -> str:
        """ Helper to return a URL to another object """
        url = resolve_url(
            admin_urlname(instance._meta, SafeText("change")), instance.pk
        )
        return format_html('<a href="{}">{}</a>', url, name or str(instance))


class ReadOnlyAdminMixin(MixinBase, ModelAdmin):
    """ Disables all editing capabilities for the model admin """

    change_form_template = "dal/admin/view.html"


class ReadOnlyTabularInlineMixin(MixinBase, TabularInline):
    """ Disables all editing capabilities for inline """

    model = None
