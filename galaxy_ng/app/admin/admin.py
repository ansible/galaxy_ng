from django.contrib import admin

from django.contrib.admin.models import LogEntry


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'action_time',
        'user',
        'content_type',
        'object_id',
        'object_repr',
        'action_flag',
        'change_message',
    )
    list_filter = ('action_time',)
    raw_id_fields = ('user', 'content_type')
