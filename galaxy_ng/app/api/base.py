from django.test.signals import setting_changed

from rest_framework import generics
from rest_framework import views
from rest_framework import viewsets
from rest_framework.settings import APISettings


# NOTE: This code uses undocumented and internal class rest_framework.settings.APISettings.
#       It must be eventually refactored.
DEFAULT_SETTINGS = {
    "GALAXY_EXCEPTION_HANDLER": "galaxy_ng.app.api.exceptions.exception_handler",
    "GALAXY_PAGINATION_CLASS": "galaxy_ng.app.api.pagination.LimitOffsetPagination",
    "GALAXY_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "GALAXY_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
IMPORT_STRINGS = [
    "GALAXY_EXCEPTION_HANDLER",
    "GALAXY_AUTHENTICATION_CLASSES",
    "GALAXY_PERMISSION_CLASSES",
    "GALAXY_PAGINATION_CLASS",
]

local_settings = APISettings(defaults=DEFAULT_SETTINGS, import_strings=IMPORT_STRINGS)


class LocalSettingsMixin:
    authentication_classes = local_settings.GALAXY_AUTHENTICATION_CLASSES
    permission_classes = local_settings.GALAXY_PERMISSION_CLASSES
    pagination_class = local_settings.GALAXY_PAGINATION_CLASS

    def get_exception_handler(self):
        return local_settings.GALAXY_EXCEPTION_HANDLER


class APIView(LocalSettingsMixin, views.APIView):
    pass


class ViewSet(LocalSettingsMixin, viewsets.ViewSet):
    pass


class GenericAPIView(LocalSettingsMixin, generics.GenericAPIView):
    pass


class GenericViewSet(LocalSettingsMixin, viewsets.GenericViewSet):
    pass


def _reload_local_settings(**kwargs):
    if kwargs["setting"] in DEFAULT_SETTINGS:
        local_settings.reload()


setting_changed.connect(_reload_local_settings)
