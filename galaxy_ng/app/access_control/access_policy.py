import logging
import os

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound

from pulpcore.plugin.access_policy import AccessPolicyFromDB

from pulp_container.app.access_policy import NamespacedAccessPolicyMixin
from pulp_container.app import models as container_models

from galaxy_ng.app import models

log = logging.getLogger(__name__)


# TODO this is a function in pulpcore that needs to get moved ot the plugin api.
# from pulpcore.plugin.util import get_view_urlpattern
def get_view_urlpattern(view):
    """
    Get a full urlpattern for a view which includes a parent urlpattern if it exists.
    E.g. for repository versions the urlpattern is just `versions` without its parent_viewset
    urlpattern.

    Args:
        view(subclass rest_framework.viewsets.GenericViewSet): The view being requested.

    Returns:
        str: a full urlpattern for a specified view/viewset
    """
    if hasattr(view, "parent_viewset") and view.parent_viewset:
        return os.path.join(view.parent_viewset.urlpattern(), view.urlpattern())
    return view.urlpattern()


class AccessPolicyBase(AccessPolicyFromDB):
    """
    This class is capable of loading access policy statements from galaxy_ng's hardcoded list of
    statements as well as from pulp's access policy database table. Priority is given to statements
    that are found in the hardcoded list of statements, so if a view name for a pulp viewset is
    found there, it will be loaded over whatever is in the database. If no viewset is found that
    matches the pulp viewset name, the statements will be loaded from the database as they would
    normally be loaded in pulp ansible.

    This class has two main functions.
    1. It is configured as the default permission class in settings.py. This means it will be used
       to load access policy definitions for all of the pulp viewsets and provides a mechanism to
       override pulp viewset access policies as well as create custom policy conditions
    2. It can be subclassed and used as a permission class for viewsets in galaxy_ng. This allows
       for custom policy conditions to be declared for specific viewsets, rather than putting them
       in the base class.
    """

    _STATEMENTS = None
    NAME = None

    @property
    def galaxy_statements(self):
        """Lazily import the galaxy_statements from the statements file."""
        if self._STATEMENTS is None:
            # import here to avoid working outside django/dynaconf settings context
            from galaxy_ng.app.access_control.statements import STANDALONE_STATEMENTS  # noqa
            from galaxy_ng.app.access_control.statements import INSIGHTS_STATEMENTS  # noqa

            self._STATEMENTS = {
                "insights": INSIGHTS_STATEMENTS,
                "standalone": STANDALONE_STATEMENTS,
            }
        return self._STATEMENTS

    def _get_statements(self):
        return self.galaxy_statements[settings.GALAXY_DEPLOYMENT_MODE]

    def get_policy_statements(self, request, view):
        statements = self._get_statements()
        if self.NAME:
            return statements.get(self.NAME, [])

        try:
            viewname = get_view_urlpattern(view)
            override_ap = statements.get(viewname, None)

            if override_ap:
                return override_ap
        except AttributeError:
            pass

        # Note: for the time being, pulp-container access policies should still be loaded from
        # the databse, because we can't override the get creation hooks like this.
        return super().get_policy_statements(request, view)

    # if not defined, defaults to parent qs of None breaking Group Detail
    def scope_queryset(self, view, qs):
        return qs

    # Define global conditions here
    def _get_rh_identity(self, request):
        if not isinstance(request.auth, dict):
            log.debug("No request rh_identity request.auth found for request %s", request)
            return False

        x_rh_identity = request.auth.get("rh_identity")
        if not x_rh_identity:
            return False

        return x_rh_identity

    def has_rh_entitlements(self, request, view, permission):

        x_rh_identity = self._get_rh_identity(request)

        if not x_rh_identity:
            log.debug(
                "No x_rh_identity found when check entitlements for request %s for view %s",
                request,
                view,
            )
            return False

        entitlements = x_rh_identity.get("entitlements", {})
        entitlement = entitlements.get(settings.RH_ENTITLEMENT_REQUIRED, {})
        return entitlement.get("is_entitled", False)

    def can_update_collection(self, request, view, permission):
        if getattr(self, "swagger_fake_view", False):
            # If OpenAPI schema is requested, don't check for update permissions
            return False
        collection = view.get_object()
        namespace = models.Namespace.objects.get(name=collection.namespace)
        return request.user.has_perm("galaxy.upload_to_namespace", namespace)

    def can_create_collection(self, request, view, permission):
        data = view._get_data(request)
        try:
            namespace = models.Namespace.objects.get(name=data["filename"].namespace)
        except models.Namespace.DoesNotExist:
            raise NotFound(_("Namespace in filename not found."))
        return request.user.has_perm("galaxy.upload_to_namespace", namespace)

    def can_sign_collections(self, request, view, permission):
        # Repository is required on the CollectionSign payload
        # Assumed that if user can modify repo they can sign everything in it
        repository = view.get_repository(request)
        can_modify_repo = request.user.has_perm('ansible.modify_ansible_repo_content', repository)

        # Payload can optionally specify a namespace to filter its contents
        # Assumed that if user has access to modify namespace they can sign its contents.
        if namespace := request.data.get('namespace'):
            try:
                namespace = models.Namespace.objects.get(name=namespace)
            except models.Namespace.DoesNotExist:
                raise NotFound(_('Namespace not found.'))
            return can_modify_repo and request.user.has_perm(
                'galaxy.upload_to_namespace', namespace
            )

        # the other filtering options are content_units and name/version
        # and falls on the same permissions as modifying the main repo
        return can_modify_repo

    def unauthenticated_collection_download_enabled(self, request, view, permission):
        return settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD

    def unauthenticated_collection_access_enabled(self, request, view, action):
        return settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS


class NamespaceAccessPolicy(AccessPolicyBase):
    NAME = "NamespaceViewSet"


class CollectionAccessPolicy(AccessPolicyBase):
    NAME = "CollectionViewSet"


class CollectionRemoteAccessPolicy(AccessPolicyBase):
    NAME = "CollectionRemoteViewSet"


class UserAccessPolicy(AccessPolicyBase):
    NAME = "UserViewSet"

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


class MyUserAccessPolicy(AccessPolicyBase):
    NAME = "MyUserViewSet"

    def is_current_user(self, request, view, action):
        return request.user == view.get_object()


class SyncListAccessPolicy(AccessPolicyBase):
    NAME = "SyncListViewSet"


class MySyncListAccessPolicy(AccessPolicyBase):
    NAME = "MySyncListViewSet"

    def is_org_admin(self, request, view, permission):
        """Check the rhn_entitlement data to see if user is an org admin"""
        x_rh_identity = self._get_rh_identity(request)

        if not x_rh_identity:
            log.debug("No x_rh_identity found for request %s for view %s", request, view)
            return False

        identity = x_rh_identity["identity"]
        user = identity["user"]
        return user.get("is_org_admin", False)


class TagsAccessPolicy(AccessPolicyBase):
    NAME = "TagViewSet"


class TaskAccessPolicy(AccessPolicyBase):
    NAME = "TaskViewSet"


class LoginAccessPolicy(AccessPolicyBase):
    NAME = "LoginView"


class LogoutAccessPolicy(AccessPolicyBase):
    NAME = "LogoutView"


class TokenAccessPolicy(AccessPolicyBase):
    NAME = "TokenView"


class GroupAccessPolicy(AccessPolicyBase):
    NAME = "GroupViewSet"


class DistributionAccessPolicy(AccessPolicyBase):
    NAME = "DistributionViewSet"


class MyDistributionAccessPolicy(AccessPolicyBase):
    NAME = "MyDistributionViewSet"


class ContainerRepositoryAccessPolicy(AccessPolicyBase):
    NAME = "ContainerRepositoryViewSet"


class ContainerReadmeAccessPolicy(AccessPolicyBase):
    NAME = "ContainerReadmeViewset"

    def has_container_namespace_perms(self, request, view, action, permission):
        readme = view.get_object()
        return request.user.has_perm(permission) or request.user.has_perm(
            permission, readme.container.namespace
        )


class ContainerNamespaceAccessPolicy(AccessPolicyBase):
    NAME = "ContainerNamespaceViewset"


class ContainerRegistryRemoteAccessPolicy(AccessPolicyBase):
    NAME = "ContainerRegistryRemoteViewSet"


class ContainerRemoteAccessPolicy(AccessPolicyBase, NamespacedAccessPolicyMixin):
    NAME = "ContainerRemoteViewSet"

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


class LandingPageAccessPolicy(AccessPolicyBase):
    NAME = "LandingPageViewSet"
