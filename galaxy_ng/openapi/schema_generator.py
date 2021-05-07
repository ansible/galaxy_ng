from pulpcore.openapi import PulpSchemaGenerator


class GalaxySchemaGenerator(PulpSchemaGenerator):
    def convert_endpoint_path_params(self, path, view, schema):
        return path
