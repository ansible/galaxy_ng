import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_access_policy import AccessPolicy
from rest_framework.exceptions import NotFound

from pulp_container.app.access_policy import NamespacedAccessPolicyMixin
from pulp_container.app import models as container_models

from galaxy_ng.app import models
from galaxy_ng.app.access_control.mixins import UnauthenticatedCollectionAccessMixin

log = logging.getLogger(__name__)


class AccessPolicyBase(AccessPolicy):

    _STATEMENTS = None

    @property
    def galaxy_statements(self):
        """Lazily import the galaxy_statements from the statements file."""
        if self._STATEMENTS is None:
            # import here to avoid working outside django/dynaconf settings context
            from galaxy_ng.app.access_control.statements import STANDALONE_STATEMENTS  # noqa
            from galaxy_ng.app.access_control.statements import INSIGHTS_STATEMENTS  # noqa
            self._STATEMENTS = {
                'insights': INSIGHTS_STATEMENTS,
                'standalone': STANDALONE_STATEMENTS
            }
        return self._STATEMENTS

    def _get_statements(self, deployment_mode):
        return self.galaxy_statements[deployment_mode]

    def get_policy_statements(self, request, view):
        statements = self._get_statements(settings.GALAXY_DEPLOYMENT_MODE)
        return statements.get(self.NAME, [])

    def _get_rh_identity(self, request):
        if not isinstance(request.auth, dict):
            log.debug("No request rh_identity request.auth found for request %s", request)
            return False

        x_rh_identity = request.auth.get('rh_identity')
        if not x_rh_identity:
            return False

        return x_rh_identity

    # used by insights access policy
    def has_rh_entitlements(self, request, view, permission):

        x_rh_identity = self._get_rh_identity(request)

        if not x_rh_identity:
            log.debug("No x_rh_identity found when check entitlements for request %s for view %s",
                      request, view)
            return False

        entitlements = x_rh_identity.get('entitlements', {})
        entitlement = entitlements.get(settings.RH_ENTITLEMENT_REQUIRED, {})
        return entitlement.get('is_entitled', False)


class NamespaceAccessPolicy(UnauthenticatedCollectionAccessMixin, AccessPolicyBase):
    NAME = 'NamespaceViewSet'


class CollectionAccessPolicy(UnauthenticatedCollectionAccessMixin, AccessPolicyBase):
    NAME = 'CollectionViewSet'

    def can_update_collection(self, request, view, permission):
        if getattr(self, "swagger_fake_view", False):
            # If OpenAPI schema is requested, don't check for update permissions
            return False
        collection = view.get_object()
        namespace = models.Namespace.objects.get(name=collection.namespace)
        return request.user.has_perm('galaxy.upload_to_namespace', namespace)

    def can_create_collection(self, request, view, permission):
        data = view._get_data(request)
        try:
            namespace = models.Namespace.objects.get(name=data['filename'].namespace)
        except models.Namespace.DoesNotExist:
            raise NotFound(_('Namespace in filename not found.'))
        return request.user.has_perm('galaxy.upload_to_namespace', namespace)

    def unauthenticated_collection_download_enabled(self, request, view, permission):
        return settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD


class CollectionRemoteAccessPolicy(AccessPolicyBase):
    NAME = 'CollectionRemoteViewSet'


class UserAccessPolicy(AccessPolicyBase):
    NAME = 'UserViewSet'

    def user_is_superuser(self, request, view, action):
        if getattr(self, "swagger_fake_view", False):
            # If OpenAPI schema is requested, don't check for superuser
            return False
        user = view.get_object()
        return user.is_superuser

    def is_current_user(self, request, view, action):
        if getattr(self, "swagger_fake_view", False):
            # If OpenAPI schema is requested, don't check for current user
            return False
        return request.user == view.get_object()


class MyUserAccessPolicy(UnauthenticatedCollectionAccessMixin, AccessPolicyBase):
    NAME = 'MyUserViewSet'

    def is_current_user(self, request, view, action):
        return request.user == view.get_object()


class SyncListAccessPolicy(AccessPolicyBase):
    NAME = 'SyncListViewSet'


class MySyncListAccessPolicy(AccessPolicyBase):
    NAME = 'MySyncListViewSet'

    def is_org_admin(self, request, view, permission):
        """Check the rhn_entitlement data to see if user is an org admin"""
        x_rh_identity = self._get_rh_identity(request)

        if not x_rh_identity:
            log.debug("No x_rh_identity found for request %s for view %s",
                      request, view)
            return False

        identity = x_rh_identity['identity']
        user = identity['user']
        return user.get('is_org_admin', False)


class TagsAccessPolicy(AccessPolicyBase):
    NAME = 'TagViewSet'


class TaskAccessPolicy(AccessPolicyBase):
    NAME = 'TaskViewSet'


class LoginAccessPolicy(AccessPolicyBase):
    NAME = 'LoginView'


class LogoutAccessPolicy(AccessPolicyBase):
    NAME = 'LogoutView'


class TokenAccessPolicy(AccessPolicyBase):
    NAME = 'TokenView'


class GroupAccessPolicy(AccessPolicyBase):
    NAME = 'GroupViewSet'


class DistributionAccessPolicy(AccessPolicyBase):
    NAME = 'DistributionViewSet'


class MyDistributionAccessPolicy(AccessPolicyBase):
    NAME = 'MyDistributionViewSet'


class ContainerRepositoryAccessPolicy(AccessPolicyBase):
    NAME = 'ContainerRepositoryViewSet'


class ContainerReadmeAccessPolicy(AccessPolicyBase):
    NAME = 'ContainerReadmeViewset'

    def has_container_namespace_perms(self, request, view, action, permission):
        readme = view.get_object()
        return (request.user.has_perm(permission)
                or request.user.has_perm(permission, readme.container.namespace))


class ContainerNamespaceAccessPolicy(AccessPolicyBase):
    NAME = 'ContainerNamespaceViewset'


class ContainerRegistryRemoteAccessPolicy(AccessPolicyBase):
    NAME = 'ContainerRegistryRemoteViewSet'


class ContainerRemoteAccessPolicy(AccessPolicyBase, NamespacedAccessPolicyMixin):
    NAME = 'ContainerRemoteViewSet'

    def has_distro_permission(self, request, view, action, permission):
        class FakeView:
            def __init__(self, obj):
                self.obj = obj

            def get_object(self):
                return self.obj

        # has_container_namespace_perms

        remote = view.get_object()
        repositories = remote.repository_set.all()

        # In theory there should never be more than one repository connected to a remote, but
        # the pulp apis don't prevent you from attaching as many remotes as you want to a repo.
        for repo in repositories:
            for distro in container_models.ContainerDistribution.objects.filter(repository=repo):
                dummy_view = FakeView(distro)
                if self.has_namespace_or_obj_perms(request, dummy_view, action, permission):
                    return True

        return False
