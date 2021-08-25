from django.conf import settings

from rest_framework import generics
from rest_framework import permissions
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
GALAXY_PAGINATION_CLASS = perform_import(
    settings.GALAXY_PAGINATION_CLASS,
    'GALAXY_PAGINATION_CLASS'
)


class _MustImplementPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        raise NotImplementedError("subclass must implement permission_classes")


class LocalSettingsMixin:
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES
    pagination_class = GALAXY_PAGINATION_CLASS
    permission_classes = [_MustImplementPermission]

    def get_exception_handler(self):
        return GALAXY_EXCEPTION_HANDLER


class APIView(LocalSettingsMixin, views.APIView):
    pass


class ViewSet(LocalSettingsMixin, viewsets.ViewSet):
    pass


class GenericAPIView(LocalSettingsMixin, generics.GenericAPIView):
    pass


class GenericViewSet(LocalSettingsMixin, viewsets.GenericViewSet):
    pass


class ModelViewSet(LocalSettingsMixin, viewsets.ModelViewSet):
    pass
