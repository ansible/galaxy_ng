import logging
import os

from django.conf import settings
from django.contrib.auth.models import Permission
from django.db.models import Q, Exists, OuterRef, CharField
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, ValidationError

from pulpcore.plugin.util import extract_pk
from pulpcore.plugin.access_policy import AccessPolicyFromDB
from pulpcore.plugin.models.role import GroupRole, UserRole
from pulpcore.plugin import models as core_models
from pulpcore.plugin.util import get_objects_for_user

from pulp_ansible.app import models as ansible_models

from pulp_container.app import models as container_models
from pulp_ansible.app.serializers import CollectionVersionCopyMoveSerializer

from galaxy_ng.app import models
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.constants import COMMUNITY_DOMAINS

from galaxy_ng.app.access_control.statements import PULP_VIEWSETS

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


def has_model_or_object_permissions(user, permission, obj):
    return user.has_perm(permission) or user.has_perm(permission, obj)


class MockPulpAccessPolicy:
    statements = None
    creation_hooks = None
    queryset_scoping = None

    def __init__(self, access_policy):
        for x in access_policy:
            setattr(self, x, access_policy[x])


class GalaxyStatements:
    _STATEMENTS = None

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

    def get_pulp_access_policy(self, name, default=None):
        """
        Converts the statement list into the full pulp access policy.
        """

        statements = self._get_statements().get(name, default)

        if not statements and default is None:
            return None

        return MockPulpAccessPolicy({
            "statements": statements,
        })


GALAXY_STATEMENTS = GalaxyStatements()


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

    NAME = None

    @classmethod
    def get_access_policy(cls, view):
        statements = GALAXY_STATEMENTS

        # If this is a galaxy access policy, load from the statement file
        if cls.NAME:
            return statements.get_pulp_access_policy(cls.NAME, default=[])

        # Check if the view has a url pattern. If it does, check for customized
        # policies from statements/pulp.py
        try:
            viewname = get_view_urlpattern(view)

            override_ap = PULP_VIEWSETS.get(viewname, None)
            if override_ap:
                return MockPulpAccessPolicy(override_ap)

        except AttributeError:
            pass

        # If no customized policies exist, try to load the one defined on the view itself
        try:
            return MockPulpAccessPolicy(view.DEFAULT_ACCESS_POLICY)
        except AttributeError:
            pass

        # As a last resort, require admin rights
        return MockPulpAccessPolicy(
            {
                "statements": [{"action": "*", "principal": "admin", "effect": "allow"}],
            }
        )

    def scope_by_view_repository_permissions(self, view, qs, field_name="", is_generic=True):
        """
        Returns objects with a repository foreign key that are connected to a public
        repository or a private repository that the user has permissions on

        is_generic should be set to True when repository is a FK to the generic Repository
        object and False when it's a FK to AnsibleRepository
        """
        user = view.request.user
        if user.has_perm("ansible.view_ansiblerepository"):
            return qs
        view_perm = Permission.objects.get(
            content_type__app_label="ansible", codename="view_ansiblerepository")

        if field_name:
            field_name = field_name + "__"

        private_q = Q(**{f"{field_name}private": False})
        if is_generic:
            private_q = Q(**{f"{field_name}ansible_ansiblerepository__private": False})
            qs = qs.select_related(f"{field_name}ansible_ansiblerepository")

        if user.is_anonymous:
            qs = qs.filter(private_q)
        else:
            user_roles = UserRole.objects.filter(user=user, role__permissions=view_perm).filter(
                object_id=OuterRef("repo_pk_str"))

            group_roles = GroupRole.objects.filter(
                group__in=user.groups.all(),
                role__permissions=view_perm
            ).filter(
                object_id=OuterRef("repo_pk_str"))

            qs = qs.annotate(
                repo_pk_str=Cast(f"{field_name}pk", output_field=CharField())
            ).annotate(
                has_user_role=Exists(user_roles)
            ).annotate(
                has_group_roles=Exists(group_roles)
            ).filter(
                private_q
                | Q(has_user_role=True)
                | Q(has_group_roles=True)
            )

        return qs

    def scope_synclist_distributions(self, view, qs):
        if not view.request.user.has_perm("galaxy.view_synclist"):
            my_synclists = get_objects_for_user(
                view.request.user,
                "galaxy.view_synclist",
                qs=models.SyncList.objects.all(),
            )
            my_synclists = my_synclists.values_list("distribution", flat=True)
            qs = qs.exclude(Q(base_path__endswith="-synclist") & ~Q(pk__in=my_synclists))
        return self.scope_by_view_repository_permissions(
            view,
            qs,
            field_name="repository",
            is_generic=True
        )

    # if not defined, defaults to parent qs of None breaking Group Detail
    def scope_queryset(self, view, qs):
        """
        Scope the queryset based on the access policy `scope_queryset` method if present.
        """
        access_policy = self.get_access_policy(view)
        if view.action == "list" and access_policy:
            # if access_policy := self.get_access_policy(view):
            if access_policy.queryset_scoping:
                scope = access_policy.queryset_scoping["function"]
                if scope == "scope_queryset" or not (function := getattr(self, scope, None)):
                    return qs
                kwargs = access_policy.queryset_scoping.get("parameters") or {}
                qs = function(view, qs, **kwargs)
        return qs

    # Define global conditions here
    def v3_can_view_repo_content(self, request, view, action):
        """
        Check if the repo is private, only let users with view repository permissions
        view the collections here.
        """

        path = view.kwargs.get(
            "distro_base_path",
            view.kwargs.get(
                "path",
                None
            )
        )

        if path:
            distro = ansible_models.AnsibleDistribution.objects.get(base_path=path)
            repo = distro.repository
            repo = repo.cast()

            if repo.private:
                perm = "ansible.view_ansiblerepository"
                return request.user.has_perm(perm) or request.user.has_perm(perm, repo)

        return True

    def has_ansible_repo_perms(self, request, view, action, permission):
        """
        Check if the user has model or object-level permissions
        on the repository or associated repository.

        View actions are only enforced when the repo is private.
        """
        if request.user.has_perm(permission):
            return True

        try:
            obj = view.get_object()
        except AssertionError:
            obj = view.get_parent_object()

        if isinstance(obj, ansible_models.AnsibleRepository):
            repo = obj

        else:
            # user can't have object permission to not existing repository
            if obj.repository is None:
                return False

            repo = obj.repository.cast()

        if permission == "ansible.view_ansiblerepository":
            if not repo.private:
                return True

        return request.user.has_perm(permission, repo)

    def can_copy_or_move(self, request, view, action, permission):
        """
        Check if the user has model or object-level permissions
        on the source and destination repositories.
        """
        if request.user.has_perm(permission):
            return True

        # accumulate all the objects to check for permission
        repos_to_check = []
        # add source repo to the list of repos to check
        obj = view.get_object()
        if isinstance(obj, ansible_models.AnsibleRepository):
            repos_to_check.append(obj)

        # add destination repos to the list of repos to check
        serializer = CollectionVersionCopyMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repos_to_check.extend(list(serializer.validated_data["destination_repositories"]))

        # have to check `repos_to_check and all(...)` because `all([])` on an empty
        # list would return True
        return repos_to_check and all(
            request.user.has_perm(permission, repo) for repo in repos_to_check
        )

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
        return has_model_or_object_permissions(
            request.user,
            "galaxy.upload_to_namespace",
            namespace
        )

    def can_create_collection(self, request, view, permission):
        data = view._get_data(request)
        try:
            namespace = models.Namespace.objects.get(name=data["filename"].namespace)
        except models.Namespace.DoesNotExist:
            raise NotFound(_("Namespace in filename not found."))

        can_upload_to_namespace = has_model_or_object_permissions(
            request.user,
            "galaxy.upload_to_namespace",
            namespace
        )

        if not can_upload_to_namespace:
            return False

        path = view._get_path()
        try:
            repo = ansible_models.AnsibleDistribution.objects.get(base_path=path).repository.cast()
            pipeline = repo.pulp_labels.get("pipeline", None)

            # if uploading to a staging repo, don't check any additional perms
            if pipeline == "staging":
                return True

            # if no pipeline is declared on the repo, verify that the user can modify the
            # repo contents.
            elif pipeline is None:
                return has_model_or_object_permissions(
                    request.user,
                    "ansible.modify_ansible_repo_content",
                    repo
                )

            # if pipeline is anything other staging, reject the request.
            return False

        except ansible_models.AnsibleDistribution.DoesNotExist:
            raise NotFound(_("Distribution does not exist."))

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
            return can_modify_repo and has_model_or_object_permissions(
                request.user,
                "galaxy.upload_to_namespace",
                namespace
            )

        # the other filtering options are content_units and name/version
        # and falls on the same permissions as modifying the main repo
        return can_modify_repo

    def unauthenticated_collection_download_enabled(self, request, view, permission):
        return settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD

    def unauthenticated_collection_access_enabled(self, request, view, action):
        return settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS

    def has_concrete_perms(self, request, view, action, permission):
        # Function the same as has_model_or_object_perms, but uses the concrete model
        # instead of the proxy model
        if request.user.has_perm(permission):
            return True

        # if the object is a proxy object, get the concrete object and use that for the
        # permission comparison
        obj = view.get_object()
        if obj._meta.proxy:
            obj = obj._meta.concrete_model.objects.get(pk=obj.pk)

        return request.user.has_perm(permission, obj)

    def signatures_not_required_for_repo(self, request, view, action):
        """
        Validate that collections are being added with signatures to approved repos
        when signatures are required.
        """
        repo = view.get_object()
        repo_version = repo.latest_version()

        if not settings.GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL:
            return True

        serializer = CollectionVersionCopyMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        signing_service = data.get("signing_service", None)

        if signing_service:
            return True

        is_any_approved = False
        for repo in data["destination_repositories"]:
            if repo.pulp_labels.get("pipeline", None) == "approved":
                is_any_approved = True
                break

        # If any destination repo is marked as approved, check that the signatures
        # are available
        if not is_any_approved:
            return True

        for cv in data["collection_versions"]:
            sig_exists = repo_version.get_content(
                ansible_models.CollectionVersionSignature.objects
            ).filter(signed_collection=cv).exists()

            if not sig_exists:
                raise ValidationError(detail={"collection_versions": _(
                    "Signatures are required in order to add collections into any 'approved'"
                    "repository when GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL is enabled."
                )})

        return True

    def is_not_protected_base_path(self, request, view, action):
        """
        Prevent deleting any of the default distributions or repositories.
        """
        PROTECTED_BASE_PATHS = (
            "rh-certified",
            "validated",
            "community",
            "published",
            "staging",
            "rejected",
        )

        obj = view.get_object()
        if isinstance(obj, core_models.Repository):
            if ansible_models.AnsibleDistribution.objects.filter(
                repository=obj,
                base_path__in=PROTECTED_BASE_PATHS,
            ).exists():
                return False
        elif isinstance(obj, core_models.Distribution):
            if obj.base_path in PROTECTED_BASE_PATHS:
                return False

        return True

    def require_requirements_yaml(self, request, view, action):

        if remote := request.data.get("remote"):
            try:
                remote = ansible_models.CollectionRemote.objects.get(pk=extract_pk(remote))

            except ansible_models.CollectionRemote.DoesNotExist:
                pass

        if not remote:
            obj = view.get_object()
            remote = obj.remote.cast()
            if remote is None:
                return True

        if not remote.requirements_file and any(
            [domain in remote.url for domain in COMMUNITY_DOMAINS]
        ):
            raise ValidationError(
                detail={
                    'requirements_file':
                        _('Syncing content from galaxy.ansible.com without specifying a '
                          'requirements file is not allowed.')
                })
        return True


class AIDenyIndexAccessPolicy(AccessPolicyBase):
    NAME = "AIDenyIndexView"

    def can_edit_ai_deny_index(self, request, view, permission):
        """This permission applies to Namespace or LegacyNamespace on ai_deny_index/."""
        object = view.get_object()
        has_permission = False
        if isinstance(object, models.Namespace):
            has_permission = has_model_or_object_permissions(
                request.user,
                "galaxy.change_namespace",
                object
            )
        elif isinstance(object, LegacyNamespace):
            has_permission = LegacyAccessPolicy().is_namespace_owner(
                request, view, permission
            )
        return has_permission


class AppRootAccessPolicy(AccessPolicyBase):
    NAME = "AppRootViewSet"


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
        return has_model_or_object_permissions(request.user, permission, readme.container.namespace)


class ContainerRegistryRemoteAccessPolicy(AccessPolicyBase):
    NAME = "ContainerRegistryRemoteViewSet"


class ContainerRemoteAccessPolicy(AccessPolicyBase):
    NAME = "ContainerRemoteViewSet"

    # Copied from pulp_container/app/global_access_conditions.py
    def has_namespace_or_obj_perms(self, request, view, action, permission):
        """
        Check if a user has a namespace-level perms or object-level permission
        """
        ns_perm = "container.namespace_{}".format(permission.split(".", 1)[1])
        if self.has_namespace_obj_perms(request, view, action, ns_perm):
            return True
        else:
            return request.user.has_perm(permission) or request.user.has_perm(
                permission, view.get_object()
            )

    # Copied from pulp_container/app/global_access_conditions.py
    def has_namespace_obj_perms(self, request, view, action, permission):
        """
        Check if a user has object-level perms on the namespace associated with the distribution
        or repository.
        """
        if request.user.has_perm(permission):
            return True
        obj = view.get_object()
        if type(obj) is container_models.ContainerDistribution:
            namespace = obj.namespace
            return request.user.has_perm(permission, namespace)
        elif type(obj) is container_models.ContainerPushRepository:
            for dist in obj.distributions.all():
                if request.user.has_perm(permission, dist.cast().namespace):
                    return True
        elif type(obj) is container_models.ContainerPushRepositoryVersion:
            for dist in obj.repository.distributions.all():
                if request.user.has_perm(permission, dist.cast().namespace):
                    return True
        return False

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


class LegacyAccessPolicy(AccessPolicyBase):
    NAME = "LegacyAccessPolicy"

    def is_namespace_owner(self, request, viewset, action):

        # let superusers do whatever they want.
        user = request.user
        if user.is_superuser:
            return True

        namespace = None
        github_user = None
        kwargs = request.parser_context['kwargs']

        # enumerate the related namespace for this request
        if '/imports/' in request.META['PATH_INFO']:
            github_user = request.data['github_user']
            namespace = LegacyNamespace.objects.filter(name=github_user).first()

        elif '/removerole/' in request.META['PATH_INFO']:

            github_user = request.query_params['github_user']
            namespace = LegacyNamespace.objects.filter(name=github_user).first()

        elif '/roles/' in request.META['PATH_INFO']:
            roleid = kwargs.get("id", kwargs.get("pk"))
            role = LegacyRole.objects.filter(id=roleid).first()
            namespace = role.namespace

        elif '/namespaces/' in request.META['PATH_INFO']:
            ns_id = kwargs['pk']
            namespace = LegacyNamespace.objects.filter(id=ns_id).first()

        elif '/ai_deny_index/' in request.META["PATH_INFO"]:
            ns_name = kwargs.get("reference", request.data.get("reference"))
            namespace = LegacyNamespace.objects.filter(name=ns_name).first()

        # allow a user to make their own namespace
        if namespace is None and github_user and user.username == github_user:
            return True

        # allow owners to do things in the namespace
        if namespace and user.username in [x.username for x in namespace.owners.all()]:
            return True

        return False
