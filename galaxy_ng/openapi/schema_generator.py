import logging

from pulpcore.openapi import PulpSchemaGenerator

log = logging.getLogger(__name__)

"""Modify the way pulpcore's PulpSchemaGenerator modifies the
   'path' item names. ie, the '{foo_href}' stuff.
"""


class GalaxySchemaGenerator(PulpSchemaGenerator):

    def convert_endpoint_path_params(self, path, view, schema):
        """
        Skip pulpcore's converting of urls into pulp hrefs
        """

        # But to detect if we are in 'bindings' mode here, we need to
        # modify how pulpcore.openapi.PulpSchemaGenerator calls
        # convert_endpoint_path_params() so it includes either the
        # 'request' object, or something indicating to use 'bindings'
        # mode.
        #
        # If in 'bindings' mode, we just call the super method as is,
        # and more or less have to also allow the invalid 'path'
        # items as well (ie, '{foo_href}' stuff)
        #
        # But to do that, we need to have the 'request' object so we
        # can tell if do it the new way or the old way.

        # if request and 'bindings' in request.params:
        #    return super().convert_endpoint_path_params(path, view, schema)

        # 'bindings' mode is used by pulp tooling to generate a
        #  openapi spec for generating the pulp client tools.
        #  However, one of the things 'bindings' does is set the
        #  supposedly unique 'OperationId' attribute to one of
        #  a few values ('list', 'create' etc). But that also
        #  makes the generated spec more invalid, so even fewer
        #  general purpose tools can use it.

        return path
