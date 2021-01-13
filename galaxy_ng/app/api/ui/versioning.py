from rest_framework import versioning

from galaxy_ng.app import constants


# We can't use rest_framework.versioning.NamespaceVersioning directly because without
# setting the allowed versions, it will always return the first part of the namespace as
# the version, which will always resolve to "galaxy"
class UIVersioning(versioning.NamespaceVersioning):

    allowed_versions = list(constants.ALL_UI_API_VERSION.keys())
