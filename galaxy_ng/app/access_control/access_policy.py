import logging

from django.conf import settings
from rest_access_policy import AccessPolicy
from rest_framework.exceptions import NotFound

from galaxy_ng.app import models

from galaxy_ng.app.access_control.statements import STANDALONE_STATEMENTS, INSIGHTS_STATEMENTS

log = logging.getLogger(__name__)

STATEMENTS = {'insights': INSIGHTS_STATEMENTS,
              'standalone': STANDALONE_STATEMENTS}


class AccessPolicyBase(AccessPolicy):
    def _get_statements(self, deployment_mode):
        return STATEMENTS[deployment_mode]

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


class NamespaceAccessPolicy(AccessPolicyBase):
    NAME = 'NamespaceViewSet'


class CollectionAccessPolicy(AccessPolicyBase):
    NAME = 'CollectionViewSet'

    # NOTE: These are really more about modifying a Repository/Distribution
    #       that contains these collections.
    # NOTE: Also really more about modifying Repositories and updating a collection
    #       and uploading a new collection version are the same thing.
    def can_update_collection(self, request, view, permission):
        collection = view.get_object()
        namespace = models.Namespace.objects.get(name=collection.namespace)
        return request.user.has_perm('galaxy.upload_to_namespace', namespace)

    # FIXME: probably need to add something like 'can_modify_repository' and/or
    #        'can_modify_distribution'. Or 'upload_to_repository', possibly
    #        for dest repo and/or inbound repos.
    def can_create_collection(self, request, view, permission):
        data = view._get_data(request)
        try:
            namespace = models.Namespace.objects.get(name=data['filename'].namespace)
        except models.Namespace.DoesNotExist:
            raise NotFound('Namespace in filename not found.')
        # FIXME: Need to change what we evaulate for perms to upload to a repository.
        #        The upload_to_namespace perm makes a lot of assumptions which will
        #        not be true anymore.
        return request.user.has_perm('galaxy.upload_to_namespace', namespace)


class CollectionRemoteAccessPolicy(AccessPolicyBase):
    NAME = 'CollectionRemoteViewSet'


class UserAccessPolicy(AccessPolicyBase):
    NAME = 'UserViewSet'

    def user_is_superuser(self, request, view, action):
        user = view.get_object()
        return user.is_superuser

    def is_current_user(self, request, view, action):
        return request.user == view.get_object()


class MyUserAccessPolicy(AccessPolicyBase):
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
