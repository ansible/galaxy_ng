import logging

from pulpcore.openapi import PulpSchemaGenerator

log = logging.getLogger(__name__)


class GalaxySchemaGenerator(PulpSchemaGenerator):

    def convert_endpoint_path_params(self, path, view, schema):
        """
        Skip pulpcore's converting of urls into pulp hrefs
        """
        # need core tweaks
        # if request and 'bindings' in request.params:
        #     return super().convert_endpoint_path_params(path, view, schema)

        return path

    # Only overridden to stick some logging in here with having to modify
    # drf_spectacular
    def _get_paths_and_endpoints(self, request):
        """
        Generate (path, method, view) given (path, method, callback) for paths.
        """
        view_endpoints = []
        for path, path_regex, method, callback in self.endpoints:
            view = self.create_view(callback, method, request)
            path = self.coerce_path(path, method, view)
            log.debug('gpae path=%s, view=%s', path, view)
            view_endpoints.append((path, path_regex, method, view))
        return view_endpoints
