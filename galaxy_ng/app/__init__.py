import logging
from pulpcore.plugin import PulpPluginAppConfig
from django.urls.exceptions import NoReverseMatch

logger = logging.getLogger(__name__)


class PulpGalaxyPluginAppConfig(PulpPluginAppConfig):
    """Entry point for the galaxy plugin."""

    name = "galaxy_ng.app"
    label = "galaxy"
    version = "4.10.0dev"
    python_package_name = "galaxy-ng"

    def ready(self):
        super().ready()
        from .signals import handlers  # noqa
        from pulp_container.app.models import ContainerNamespace, ContainerRepository
        from pulpcore.plugin.models import Task
        from ansible_base.rbac import permission_registry

        permission_registry.register(
            ContainerNamespace,
            ContainerRepository,
            Task,
            parent_field_name=None
        )

        add_required_dab_attributes_to_models()


def add_required_dab_attributes_to_models():
    """DAB Expects Content Types to expose some methods.

    summary_fields: dict containing id, name + relevant data
    get_absolute_url: Despite the name, the relative reverse URL for object

    Apps must be ready to start importing and patching models.
    """
    from ansible_base.rbac import models as dab_rbac_models
    from ansible_base.lib.utils.models import user_summary_fields
    from ansible_base.lib.utils.response import get_relative_url
    from pulp_ansible.app import models as pulp_ansible_models
    from pulp_container.app import models as pulp_container_models
    from pulpcore.plugin import models as pulpcore_models

    from galaxy_ng.app.models import collectionimport as galaxy_collectionimport_models
    from galaxy_ng.app.models import container as galaxy_container_models
    from galaxy_ng.app.models import namespace as galaxy_namespace_models
    from galaxy_ng.app.models import organization as org_team_models
    from galaxy_ng.app.models.auth import User

    User.add_to_class('summary_fields', user_summary_fields)

    common_summary_fields = ("pk", "name")
    model_mapping = {
        pulpcore_models.Task: {
            "summary_fields": common_summary_fields,
            "reverse_name": "galaxy:api:v3:tasks-detail"
        },
        pulp_ansible_models.AnsibleDistribution: {
            "summary_fields": common_summary_fields,
            "reverse_name": "distributions-ansible/ansible-detail"
        },
        pulp_ansible_models.AnsibleCollectionDeprecated: {
            "summary_fields": common_summary_fields,
            "reverse_name": "content-ansible/collection_deprecations-detail"
        },
        pulp_ansible_models.AnsibleNamespaceMetadata: {
            "summary_fields": common_summary_fields,
        },
        pulp_ansible_models.Tag: {
            "summary_fields": common_summary_fields,
        },
        pulp_ansible_models.AnsibleNamespace: {
            "summary_fields": common_summary_fields,
            "reverse_name": "pulp_ansible/namespaces-detail"
        },
        pulp_ansible_models.CollectionVersionSignature: {
            "summary_fields": ("pk", "pubkey_fingerprint"),
            "reverse_name": "content-ansible/collection_signatures-detail"
        },
        pulp_ansible_models.CollectionVersion: {
            "summary_fields": common_summary_fields + ("version",),
            "reverse_name": "content-ansible/collection_versions-detail"
        },
        pulp_ansible_models.Collection: {
            "summary_fields": common_summary_fields + ("namespace",),
            "reverse_name": "ansible/collections-detail"
        },
        pulp_ansible_models.CollectionRemote: {
            "summary_fields": common_summary_fields,
            "reverse_name": "remotes-ansible/collection-detail"
        },
        pulp_ansible_models.AnsibleRepository: {
            "summary_fields": common_summary_fields,
            "reverse_name": "repositories-ansible/ansible-detail"
        },
        galaxy_collectionimport_models.CollectionImport: {
            "summary_fields": common_summary_fields + ("version",),
            "reverse_name": "galaxy:api:v3:collection-imports-detail"
        },
        galaxy_namespace_models.NamespaceLink: {
            "summary_fields": common_summary_fields,
        },
        galaxy_namespace_models.Namespace: {
            "summary_fields": common_summary_fields,
            "reverse_name": "galaxy:api:v3:namespaces-detail",
            "reverse_args": ("name",)
        },
        galaxy_container_models.ContainerDistroReadme: {
            "summary_fields": ("pk",),
        },
        galaxy_container_models.ContainerNamespace: {
            "summary_fields": common_summary_fields,
            "reverse_name": "pulp_container/namespaces-detail"
        },
        galaxy_container_models.ContainerRegistryRemote: {
            "summary_fields": common_summary_fields,
            "reverse_name": "galaxy_ng/registry-remote-detail"
        },
        galaxy_container_models.ContainerRegistryRepos: {
            "summary_fields": ("pk",),
        },
        pulp_container_models.ContainerDistribution: {
            "summary_fields": common_summary_fields,
            "reverse_name": "distributions-container/container-detail"
        },
        pulp_container_models.ContainerNamespace: {
            "summary_fields": common_summary_fields,
            "reverse_name": "pulp_container/namespaces-detail"
        },
        pulp_container_models.ContainerRepository: {
            "summary_fields": common_summary_fields,
            # "reverse_name": "repositories-container/container-detail"
            "reverse_name": "galaxy:api:v3:container-repository-detail",
            "reverse_args": ("base_path",)
        },
        dab_rbac_models.RoleUserAssignment: {
            "reverse_name": "galaxy:api:ui_v2:roleuserassignment-detail"
        },
        dab_rbac_models.RoleTeamAssignment: {
            "reverse_name": "galaxy:api:ui_v2:roleteamassignment-detail"
        },
        dab_rbac_models.RoleDefinition: {
            "reverse_name": "galaxy:api:ui_v2:roledefinition-detail"
        },
        org_team_models.Team: {"reverse_name": "galaxy:api:ui_v2:team-detail"},
        User: {"reverse_name": "galaxy:api:ui_v2:user-detail"},
    }

    def summary_fields(obj):
        return {
            "id" if field == "pk" else field: getattr(obj, field)
            for field in model_mapping[obj.__class__]["summary_fields"]
        }

    def get_absolute_url(obj):
        reverse_name = model_mapping[obj.__class__]["reverse_name"]
        reverse_args = model_mapping[obj.__class__].get("reverse_args", ("pk",))
        kwargs = {k: getattr(obj, k) for k in reverse_args}
        try:
            return get_relative_url(reverse_name, kwargs=kwargs)
        except NoReverseMatch:
            logger.debug(
                f"Tried to reverse {reverse_name} for model "
                f"{obj.__class__.__name__} but said view is not defined"
            )
            return ''

    for model_class, data in model_mapping.items():

        if "summary_fields" in data and getattr(model_class, "summary_fields", None) is None:
            model_class.add_to_class("summary_fields", summary_fields)

        if "reverse_name" in data and getattr(model_class, "get_absolute_url", None) is None:
            model_class.add_to_class("get_absolute_url", get_absolute_url)
