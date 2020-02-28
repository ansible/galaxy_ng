import galaxy_pulp
from rest_framework import viewsets

from pulp_galaxy.app.common import pulp


class TagsViewSet(viewsets.GenericViewSet):

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
