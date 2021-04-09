import logging
from typing import List

from django.conf import settings
from rest_access_policy import AccessPolicy, AccessPolicyException
from rest_framework.exceptions import NotFound

from galaxy_ng.app import models

from galaxy_ng.app.access_control.statements import STANDALONE_STATEMENTS, INSIGHTS_STATEMENTS

log = logging.getLogger(__name__)

STATEMENTS = {'insights': INSIGHTS_STATEMENTS,
              'standalone': STANDALONE_STATEMENTS}


class AccessPolicyVerboseMixin:
    """Mixin to make AccessPolicy checks verbose

    This has to reimplement / cut&paste most of rest_access_policy.AccessPolicy
    to instrument the low level permissions checks.
    """

    def has_permission(self, request, view):
        result = super().has_permission(request, view)
        log.debug('"%s" perm check was %s for "%s %s" view="%s-%s-%s" for user="%s" with groups=%s',
                  self.NAME,
                  result,
                  request._request.method,
                  request._request.path,
                  getattr(view, 'basename', 'NotAViewSet'),
                  getattr(view, 'action', 'NotAViewSet'),
                  getattr(view, 'detail', 'NotAViewSet'),
                  request.user, ','.join([x.name for x in request.user.groups.all()]),
                  )
        return result

    def has_object_permission(self, request, view, obj):
        result = super().has_object_permission(request, view, obj)
        log.debug('"%s" %s %s view=%s-%s-%s for user=%s, groups=%s obj=%s had result: %s',
                  self.NAME,
                  request._request.method,
                  request._request.path,
                  view.basename, view.action, view.detail,
                  request.user,
                  ','.join([x.name for x in request.user.groups.all()]),
                  obj,
                  result)
        return result

    def _evaluate_statements(
        self, statements: List[dict], request, view, action: str
    ) -> bool:

        statements = self._normalize_statements(statements)

        user = request.user
        user_groups = self.get_user_group_values(user)

        matched = self._get_statements_matching_principal(request, statements)
        matched_principals = set()
        for match in matched:
            for principal in match['principal']:
                matched_principals.add(principal)

        log.debug('"%s" user "%s" in groups %s matched access policy principals %s',
                  self.NAME,
                  request.user,
                  ",".join(['"%s"' % ug for ug in user_groups]),
                  matched_principals)

        matched = self._get_statements_matching_action(request, action, matched)

        log.debug('"%s" action "%s" matched statements %s',
                  self.NAME, action, matched)

        matched = self._get_statements_matching_context_conditions(
            request, view, action, matched
        )

        denied = [_ for _ in matched if _["effect"] != "allow"]

        if len(matched) == 0 or len(denied) > 0:
            return False

        return True

    def _check_condition(self, condition: str, request, view, action: str):
        """
            Evaluate a custom context condition; if method does not exist on
            the access policy class, then return False.
            Condition value can contain a value that is passed to method, if
            formatted as `<method_name>:<arg_value>`.
        """

        parts = condition.split(":", 1)
        method_name = parts[0]
        arg = parts[1] if len(parts) == 2 else None

        method = self._get_condition_method(method_name)

        if arg is not None:
            result = method(request, view, action, arg)
        else:
            result = method(request, view, action)

        if type(result) is not bool:
            raise AccessPolicyException(
                "condition '%s' must return true/false, not %s"
                % (condition, type(result))
            )

        res_blurb = "failed"
        if result:
            res_blurb = "passed"

        log.debug('"%s" action "%s" for user "%s" %s conditions "%s"',
                  self.NAME,
                  action,
                  request.user,
                  res_blurb,
                  condition,
                  )

        return result

    def _get_statements_matching_principal(
        self, request, statements: List[dict]
    ) -> List[dict]:
        user = request.user
        user_roles = None
        matched = []

        for statement in statements:
            principals = statement["principal"]
            found = False

            if "*" in principals:
                found = True
            elif "authenticated" in principals:
                found = not user.is_anonymous
            elif "anonymous" in principals:
                found = user.is_anonymous
            elif self.id_prefix + str(user.pk) in principals:
                found = True
            else:
                log.debug("No '*', 'authenticated', 'anonymous', or user id in %s,"
                          + "trying groups %s",
                          principals,
                          user_roles)

                if not user_roles:
                    user_roles = self.get_user_group_values(user)

                for user_role in user_roles:
                    if self.group_prefix + user_role in principals:
                        found = True
                        break

            if found:
                matched.append(statement)

        return matched


class AccessPolicyBase(AccessPolicyVerboseMixin, AccessPolicy):
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
