import logging
import pprint

from django.conf import settings

from rest_framework import exceptions
from rest_framework import generics
from rest_framework import permissions
from rest_framework import views
from rest_framework import viewsets
from rest_framework.settings import perform_import

from rest_access_policy import AccessPolicy

from galaxy_ng.app.api.exceptions import AccessPolicyPermissionDenied

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

log = logging.getLogger(__name__)


class _MustImplementPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        raise NotImplementedError("subclass must implement permission_classes")


class LocalSettingsMixin:
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES
    pagination_class = GALAXY_PAGINATION_CLASS
    permission_classes = [_MustImplementPermission]

    # NOTE: If we add a drf.exceptions.PermissionDenied subclass with extra info
    #       we could make use of it in the exception_handle (esp combine with extra
    #       context from get_exception_handler_context)
    def get_exception_handler(self):
        return GALAXY_EXCEPTION_HANDLER

    def get_exception_handler_context(self):
        """
        Returns a dict that is passed through to EXCEPTION_HANDLER,
        as the `context` argument.

        This includes the sta
        """

        context = super().get_exception_handler_context()

        # Include the deployment mode and AccessPolicy in exception context for
        # better errors
        # access_policy = None
        # for permission in self.get_permissions():
        #     if isinstance(permission, AccessPolicy):
        #         access_policy = permission
        #         break

        # access_policy_data = {}
        # if access_policy:
        #     access_policy_data['name'] = access_policy.NAME
        #     access_policy_data['statements'] = \
        #         access_policy.get_policy_statements(context['request'],
        #                                             context['view'])
        #     access_policy_data['matched'] = access_policy.matched

        context['deployment_mode'] = getattr(settings, 'GALAXY_DEPLOYMENT_MODE', None)
        # context['access_policy'] = access_policy_data

        # import pprint
        # log.debug('context:\n%s', pprint.pformat(context))
        # log.debug('access_policy: %s', access_policy)
        # log.debug('id(access_policy): %s', id(access_policy))
        return context

    # This are the from the drf view/viewset classes that are used to raise
    # NotFound (404) or PermissionDenied (403) exceptions on authz/perms/access_policy fails
    #
    # To get extra detail in the rest reponse errors, we need to extend some of these.

    # NOTE: we could extend initial / finalize_response if we need to store extra
    #       info on the Request object  (possibly in liue of adding state to AccessPolicy
    #       permission objects)

    # TODO: raise a custom PermissionDenied that can hold extra detail/context
    def permission_denied(self, request, message=None, code=None, permission=None):
        """
        If request is not permitted, determine what kind of exception to raise.
        """
        if request.authenticators and not request.successful_authenticator:
            raise exceptions.NotAuthenticated()
        log.debug('our permission_denied locals:\n%s', pprint.pformat(locals()))
        log.debug('stack', stack_info=True)
        log.debug('perms instance: %s', permission)
        log.debug('perms.denied: %s', permission.denied)
        raise AccessPolicyPermissionDenied(detail=message, code=code, permission=permission)

    # TODO: likely don't need throttled yet, but it could be extended in similar way
    def throttled(self, request, wait):
        """
        If request is throttled, determine what kind of exception to raise.
        """
        raise exceptions.Throttled(wait)

    # TODO: make these pass needed info to permission_denied
    #       - possible the permission instance itself or some
    #         of it's data
    def check_permissions(self, request):
        """
        Check if the request should be permitted.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in self.get_permissions():
            log.debug('permission instance: %s', permission)
            if not permission.has_permission(request, self):
                self.permission_denied(
                    request,
                    message=getattr(permission, 'message', None),
                    code=getattr(permission, 'code', None),
                    permission=permission
                )

    def check_object_permissions(self, request, obj):
        """
        Check if the request should be permitted for a given object.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in self.get_permissions():
            log.debug('object permission instance: %s', permission)
            if not permission.has_object_permission(request, self, obj):
                self.permission_denied(
                    request,
                    message=getattr(permission, 'message', None),
                    code=getattr(permission, 'code', None),
                    permission=permission
                )

    # NOTE: For my reference to remind me each request returns a list of
    #       new instances of any of the permission classes (ie, AccessPolicy for us)
    # def get_permissions(self):
    #     """
    #     Instantiates and returns the list of permissions that this view requires.
    #     """
    #     return [permission() for permission in self.permission_classes]


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
