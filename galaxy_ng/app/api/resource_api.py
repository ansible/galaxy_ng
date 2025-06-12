from ansible_base.resource_registry.registry import (
    ResourceConfig,
    ServiceAPIConfig,
    SharedResource,
)
from ansible_base.resource_registry.shared_types import (
    FeatureFlagType,
    OrganizationType,
    TeamType,
    UserType,
)
from ansible_base.feature_flags.models import AAPFlag
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
        AAPFlag,
        shared_resource=SharedResource(serializer=FeatureFlagType, is_provider=False),
    ),
)
