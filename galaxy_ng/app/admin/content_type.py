
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from .base import BaseModelAdmin


# ContentType is not a Pulp model, so no pulp_id etc, use BaseModelAdmin
@admin.register(ContentType)
class ContentTypeAdmin(BaseModelAdmin):
    list_display = ("id", "app_label", "model")
