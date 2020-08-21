import galaxy_pulp

from pulp_ansible.app.serializers import TagSerializer

from galaxy_ng.app.common import pulp
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app.api.ui import versioning


class TagsViewSet(api_base.GenericViewSet):
    serializer_class = TagSerializer
    permission_classes = [access_policy.TagsAccessPolicy]
    versioning_class = versioning.UIVersioning

    def list(self, request, *args, **kwargs):
        self.paginator.init_from_request(request)

        params = self.request.query_params.dict()
        params.update({
            'offset': self.paginator.offset,
            'limit': self.paginator.limit,
        })

        api = galaxy_pulp.PulpTagsApi(pulp.get_client())
        response = api.list(**params)

        return self.paginator.paginate_proxy_response(response.results, response.count)
