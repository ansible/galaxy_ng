from ansible_base.resource_registry.registry import (
    ResourceConfig,
    ServiceAPIConfig,
    SharedResource,
)
from ansible_base.resource_registry.shared_types import OrganizationType, TeamType, UserType


from ansible_base.resource_registry.models import Resource, service_id

from ansible_base.resource_registry.serializers import ValidateLocalUserSerializer

from ansible_base.resource_registry.shared_types import UserType, TeamType
from galaxy_ng.app import models


class APIConfig(ServiceAPIConfig):
    service_type = "galaxy"

    @staticmethod
    def get_local_user_details(user) -> ValidateLocalUserSerializer:
        user_resource = Resource.get_resource_for_object(user)
        team_memberships = []

        for group in user.groups.all():
            resource = Resource.get_resource_for_object(group)
            team_memberships.append(
                {"ansible_id": resource.ansible_id, "membership_type": "member"}
            )

        data = {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_superuser": user.is_superuser,
            "service_id": user_resource.service_id,
            "ansible_id": user_resource.ansible_id,
            "organizations": [],
            "teams": team_memberships,
        }

        return ValidateLocalUserSerializer(data)


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
