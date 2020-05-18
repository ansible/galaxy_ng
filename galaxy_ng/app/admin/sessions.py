from django.contrib import admin

from django.contrib.sessions.models import Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'session_data', 'expire_date')
    list_filter = ('expire_date',)
