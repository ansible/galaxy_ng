from django.contrib import admin

from pulpcore.app.admin import TaskAdmin
from pulpcore.plugin.models import Task


site = admin.AdminSite(name="galaxy-admin")
site.register(Task, TaskAdmin)
