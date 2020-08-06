from django.conf import settings
from rest_access_policy import AccessPolicy

from galaxy_ng.app import models
from galaxy_ng.app import constants

from galaxy_ng.app.access_control.statements import STANDALONE_STATEMENTS, INSIGHTS_STATEMENTS


class AccessPolicyBase(AccessPolicy):
    def get_policy_statements(self, request, view):
        if (settings.GALAXY_DEPLOYMENT_MODE
                == constants.DeploymentMode.INSIGHTS.value):

            return INSIGHTS_STATEMENTS.get(self.NAME, [])
        else:
            return STANDALONE_STATEMENTS.get(self.NAME, [])

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

    def can_upload_to_namespace(self, request, view, permission):
        namespace = None

        # hack to check if view is CollectionUploadViewSet without creating
        # circular imports
        has_get_data = getattr(view, '_get_data', None)
        if has_get_data:
            data = view._get_data(request)
            namespace = models.Namespace.objects.get(name=data['filename'].namespace)
        else:
            collection = view.get_object()
            namespace = models.Namespace.objects.get(name=collection.namespace)

        return request.user.has_perm('galaxy.upload_to_namespace', namespace)


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


class GroupAccessPolicy(AccessPolicyBase):
    NAME = 'GroupViewSet'


class TaskAccessPolicy(AccessPolicyBase):
    NAME = 'TaskViewSet'


class LoginAccessPolicy(AccessPolicyBase):
    NAME = 'LoginView'


class LogoutAccessPolicy(AccessPolicyBase):
    NAME = 'LogoutView'


class TokenAccessPolicy(AccessPolicyBase):
    NAME = 'TokenView'
