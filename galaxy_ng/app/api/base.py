from django.conf import settings

from rest_framework import views
from rest_framework import viewsets
from rest_framework.settings import perform_import


GALAXY_EXCEPTION_HANDLER = perform_import(
    settings.GALAXY_EXCEPTION_HANDLER,
    'GALAXY_EXCEPTION_HANDLER'
)
GALAXY_AUTHENTICATION_CLASSES = perform_import(
    settings.GALAXY_AUTHENTICATION_CLASSES,
    'GALAXY_AUTHENTICATION_CLASSES'
)
GALAXY_PERMISSION_CLASSES = perform_import(
    settings.GALAXY_PERMISSION_CLASSES,
    'GALAXY_PERMISSION_CLASSES',
)
GALAXY_PAGINATION_CLASS = perform_import(
    settings.GALAXY_PAGINATION_CLASS,
    'GALAXY_PAGINATION_CLASS'
)


class LocalSettingsMixin:
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES
    permission_classes = GALAXY_PERMISSION_CLASSES
    pagination_class = GALAXY_PAGINATION_CLASS

    def get_exception_handler(self):
        return GALAXY_EXCEPTION_HANDLER


class APIView(LocalSettingsMixin, views.APIView):
    pass


class ViewSet(LocalSettingsMixin, viewsets.ViewSet):
    pass


class GenericViewSet(LocalSettingsMixin, viewsets.GenericViewSet):
    pass
