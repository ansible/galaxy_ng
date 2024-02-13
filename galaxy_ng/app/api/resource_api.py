from ansible_base.resource_registry.registry import (
    ResourceConfig,
    ServiceAPIConfig,
    SharedResource,
)
from ansible_base.resource_registry.shared_types import UserType, TeamType
from galaxy_ng.app import models


class APIConfig(ServiceAPIConfig):
    service_type = "galaxy"


RESOURCE_LIST = (
    ResourceConfig(
        models.auth.User,
        shared_resource=SharedResource(
            serializer=UserType,
            is_provider=False
        ),
        name_field="username"
    ),
    ResourceConfig(
        models.auth.Group,
        shared_resource=SharedResource(
            serializer=TeamType,
            is_provider=True
        ),
        name_field="name"
    ),
)
