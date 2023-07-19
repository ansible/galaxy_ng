"""
Everything related to the admin interface of RequestEvent is located in here
"""
from django.contrib.admin import register, RelatedOnlyFieldListFilter

from automated_logging.admin.base import ReadOnlyAdminMixin, ReadOnlyTabularInlineMixin
from automated_logging.models import RequestEvent


@register(RequestEvent)
class RequestEventAdmin(ReadOnlyAdminMixin):
    """ admin page specification for the RequestEvent """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.readonly_fields = [*self.readonly_fields, 'get_uri', 'get_user']

    def get_id(self, instance):
        """ shorten the id to the first 8 digits """
        return str(instance.id).split('-')[0]

    get_id.short_description = 'UUID'

    def get_uri(self, instance):
        """ get the uri. just a redirect to set the short description. """
        return instance.uri

    get_uri.short_description = 'URI'

    def get_user(self, instance):
        """ get the user with a URL """
        return self.model_admin_url(instance.user)

    get_user.short_description = 'User'

    list_display = ('get_id', 'updated_at', 'user', 'method', 'status', 'uri')

    date_hierarchy = 'updated_at'
    ordering = ('-updated_at',)

    list_filter = ('updated_at', ('user', RelatedOnlyFieldListFilter))

    fieldsets = (
        ('Information', {'fields': ('id', 'get_user', 'updated_at', 'application',)},),
        ('HTTP', {'fields': ('method', 'status', 'get_uri')}),
    )
    # TODO: Context
