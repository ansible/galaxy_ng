from ansible_base.resource_registry.registry import (
    ResourceConfig,
    ServiceAPIConfig,
    SharedResource,
)
from ansible_base.resource_registry.shared_types import OrganizationType, TeamType, UserType


from ansible_base.resource_registry.shared_types import UserType, TeamType
from galaxy_ng.app import models


from ansible_base.resource_registry.utils.resource_type_processor import ResourceTypeProcessor


class UserMapper:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class GalaxyUserProcessor(ResourceTypeProcessor):
    def pre_serialize_additional(self):
        teams = models.Team.objects.filter(group__pk__in=self.instance.groups.all())

        user = UserMapper(
            username=self.instance.username,
            email=self.instance.email,
            first_name=self.instance.first_name,
            last_name=self.instance.last_name,
            is_superuser=self.instance.is_superuser,
            external_auth_provider=None,
            external_auth_uid=None,
            organizations=[],
            teams=teams,
            organizations_administered=[],
            teams_administered=[],
        )

        return user


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
