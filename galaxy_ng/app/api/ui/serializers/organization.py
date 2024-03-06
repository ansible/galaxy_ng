from rest_framework.serializers import ModelSerializer

from galaxy_ng.app import models


class OrganizationRepositorySerializer(ModelSerializer):
    class Meta:
        model = models.OrganizationRepository
        fields = ("repository",)


class OrganizationRepositoryCreateSerializer(ModelSerializer):
    class Meta:
        model = models.OrganizationRepository
        fields = ("repository", "organization")
        extra_kwargs = {
            "organization": {"write_only": True},
        }
