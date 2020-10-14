from pulp_ansible.app.models import Tag
from pulp_ansible.app.serializers import TagSerializer

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app.api.ui import versioning


class TagsViewSet(api_base.GenericViewSet):
    serializer_class = TagSerializer
    permission_classes = [access_policy.TagsAccessPolicy]
    versioning_class = versioning.UIVersioning

    queryset = Tag.objects.all()

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)
