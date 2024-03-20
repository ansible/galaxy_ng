from ansible_base.resource_registry.registry import (
    ResourceConfig,
    ServiceAPIConfig,
    SharedResource,
)
from ansible_base.resource_registry.shared_types import OrganizationType, TeamType, UserType


from ansible_base.resource_registry.shared_types import UserType, TeamType
from galaxy_ng.app import models

from ansible_base.resource_registry.utils.resource_type_processor import ResourceTypeProcessor


class GalaxyUserProcessor(ResourceTypeProcessor):
    def pre_serialize_additional(self):
        setattr(self.instance, "external_auth_provider", None)
        setattr(self.instance, "external_auth_uid", None)
        setattr(self.instance, "organizations", [])
        setattr(self.instance, "organizations_administered", [])
        setattr(self.instance, "teams_administered", [])
        setattr(self.instance, "teams", self.instance.groups)

        return self.instance


class APIConfig(ServiceAPIConfig):

    custom_resource_processors = {"shared.user": GalaxyUserProcessor}

    service_type = "galaxy"


RESOURCE_LIST = (
    ResourceConfig(
        models.auth.User,
        shared_resource=SharedResource(serializer=UserType, is_provider=False),
        name_field="username",
    ),
    ResourceConfig(
        models.Team,
        shared_resource=SharedResource(serializer=TeamType, is_provider=False),
        name_field="name",
    ),
    ResourceConfig(
        models.Organization,
        shared_resource=SharedResource(serializer=OrganizationType, is_provider=False),
        name_field="name",
    ),
)
