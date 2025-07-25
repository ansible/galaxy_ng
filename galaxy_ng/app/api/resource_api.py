from ansible_base.resource_registry.registry import (
    ResourceConfig,
    ServiceAPIConfig,
    SharedResource,
)
from ansible_base.resource_registry.shared_types import OrganizationType, TeamType, UserType

# RBAC models
from ansible_base.rbac.models import RoleDefinition
from ansible_base.resource_registry.shared_types import RoleDefinitionType

from galaxy_ng.app import models


class APIConfig(ServiceAPIConfig):
    service_type = "galaxy"


RESOURCE_LIST = (
    ResourceConfig(
        models.auth.User,
        shared_resource=SharedResource(serializer=UserType, is_provider=False),
        name_field="username",
    ),
    ResourceConfig(
        models.Team,
        shared_resource=SharedResource(serializer=TeamType, is_provider=True),
        name_field="name",
    ),
    ResourceConfig(
        models.Organization,
        shared_resource=SharedResource(serializer=OrganizationType, is_provider=False),
        name_field="name",
    ),
    ResourceConfig(
        RoleDefinition,
        shared_resource=SharedResource(serializer=RoleDefinitionType, is_provider=True),
    ),
)
