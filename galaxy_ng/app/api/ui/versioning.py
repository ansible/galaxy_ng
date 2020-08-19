from rest_framework import versioning

from galaxy_ng.app import constants


# We can't use rest_framework.versioning.NamespaceVersioning directly because without
# setting the allowed versions, it will always return the first part of the namespace as
# the version, which will always resolve to "galaxy"
class UIVersioning(versioning.NamespaceVersioning):

    # TODO: remove old_ui from list of acceptable versions. This is here to prevent
    # the legacy v3/_ui endpoints from breaking
    allowed_versions = list(constants.ALL_UI_API_VERSION.keys()) + ['old_ui']
