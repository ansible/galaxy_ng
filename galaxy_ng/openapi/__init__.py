from django.conf import settings
from pulpcore.openapi import PulpSchemaGenerator


class GalaxySchemaGenerator(PulpSchemaGenerator):
    """Galaxy Schema Generator."""

    def convert_endpoint_path_params(self, path, view, schema):
        """Bypass variable-ization of paths if not a pulp route"""
        if hasattr(self, '_input_request'):
            if (
                self._input_request.path.startswith(settings.GALAXY_API_PATH_PREFIX)
                and not self._input_request.path.startswith(settings.API_ROOT)
            ):
                return path
        return super().convert_endpoint_path_params(path, view, schema)

    def get_schema(self, request=None, public=False):
        """Munge pulp's get_schema result"""
        self._input_request = request
        schema = super().get_schema(request=request, public=public)

        if (
            self._input_request.path.startswith(settings.GALAXY_API_PATH_PREFIX)
            and not self._input_request.path.startswith(settings.API_ROOT)
        ):
            return self.dedupe_operationIds(schema)
        return schema

    def dedupe_operationIds(self, schema):
        """Ensure all path+method operationIds are unique"""

        # group paths+methods by operationId
        operation_ids = {}
        for pk in schema['paths'].keys():
            for method, method_info in schema['paths'][pk].items():
                operationId = method_info['operationId']
                if operationId not in operation_ids:
                    operation_ids[operationId] = []
                operation_ids[operationId].append((pk, method))

        # make a new operationId for any duplicates
        for k, v in operation_ids.items():
            if len(v) < 2:
                continue
            for x in v:
                orig = schema['paths'][x[0]][x[1]]['operationId']
                schema['paths'][x[0]][x[1]]['operationId'] = \
                    self.flatten_path(x[0]) + '_' + orig

        return schema

    def flatten_path(self, path):
        """Assemble a new operationId prefix from a given path"""
        paths = [x for x in path.split('/')]
        return '_'.join(paths[:-1])
