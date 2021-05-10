import logging

from pulpcore.openapi import PulpSchemaGenerator

log = logging.getLogger(__name__)


class GalaxySchemaGenerator(PulpSchemaGenerator):
    def __init__(self, *args, **kwargs):
        self.repeated_paths = {}
        super().__init__(*args, **kwargs)

    def convert_endpoint_path_params(self, path, view, schema):
        try:
            action = view.action
        except AttributeError:
            action = None

        log.debug('(path,action)=(%s, %s)', path, action)
        if (path, action) in self.repeated_paths:
            log.debug('REPEATED PATH=%s, action=%s', path, action)
            return super().convert_endpoint_path_params(path, view, schema)

        self.repeated_paths[(path, action)] = (path, action)
        # if "_href}" in path:
        #     return super().convert_endpoint_path_params(path, view, schema)
        return path

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
            # Add pulp api endpoints twice if in 'bindings mode'
            if request:
                log.debug('request.query_params=%s', request.query_params)
            if request and "bindings" in request.query_params and path.startswith('/pulp'):
                view_endpoints.append((path, path_regex, method, view))

        return view_endpoints
