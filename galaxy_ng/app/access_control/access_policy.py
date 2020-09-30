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

    # used by insights access policy
    def has_rh_entitlements(self, request, view, permission):
        if not isinstance(request.auth, dict):
            return False
        header = request.auth.get('rh_identity')
        if not header:
            return False
        entitlements = header.get('entitlements', {})
        entitlement = entitlements.get(settings.RH_ENTITLEMENT_REQUIRED, {})
        return entitlement.get('is_entitled', False)


class NamespaceAccessPolicy(AccessPolicyBase):
    NAME = 'NamespaceViewSet'


class CollectionAccessPolicy(AccessPolicyBase):
    NAME = 'CollectionViewSet'

    def can_update_collection(self, request, view, permission):
        collection = view.get_object()
        namespace = models.Namespace.objects.get(name=collection.namespace)
        return request.user.has_perm('galaxy.upload_to_namespace', namespace)

    def can_create_collection(self, request, view, permission):
        data = view._get_data(request)
        try:
            namespace = models.Namespace.objects.get(name=data['filename'].namespace)
        except models.Namespace.DoesNotExist:
            raise NotFound('Namespace in filename not found.')
        return request.user.has_perm('galaxy.upload_to_namespace', namespace)


class CollectionRemoteAccessPolicy(AccessPolicyBase):
    NAME = 'CollectionRemoteViewSet'


class UserAccessPolicy(AccessPolicyBase):
    NAME = 'UserViewSet'

    def is_current_user_or_has_perms(self, request, view, action, permission):
        if (request.user.has_perm(permission)):
            return True

        return self.is_current_user(request, view, action)

    def is_current_user(self, request, view, action):
        return request.user == view.get_object()


class SyncListAccessPolicy(AccessPolicyBase):
    NAME = 'SyncListViewSet'


class MySyncListAccessPolicy(AccessPolicyBase):
    NAME = 'MySyncListViewSet'


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
