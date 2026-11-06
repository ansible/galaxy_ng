from django.conf import settings
from django.utils.cache import patch_vary_headers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from galaxy_ng.app.api import base as api_base

PUBLIC_SETTINGS = (
    "GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS",
    "GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD",
)


def _private_response(data):
    response = Response(data)
    response["Cache-Control"] = "private"
    patch_vary_headers(response, ("Authorization", "Cookie"))
    return response


class SettingsView(api_base.APIView):
    # Public browsing needs these values before login.
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _private_response({name: settings.get(name, False) for name in PUBLIC_SETTINGS})

        keyset = [
            *PUBLIC_SETTINGS,
            "GALAXY_API_SPEC_REQUIRE_AUTHENTICATION",
            "GALAXY_FEATURE_FLAGS",
            "GALAXY_TOKEN_EXPIRATION",
            "GALAXY_REQUIRE_CONTENT_APPROVAL",
            "GALAXY_COLLECTION_SIGNING_SERVICE",
            "GALAXY_AUTO_SIGN_COLLECTIONS",
            "GALAXY_SIGNATURE_UPLOAD_ENABLED",
            "GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL",
            "GALAXY_MINIMUM_PASSWORD_LENGTH",
            "GALAXY_AUTH_LDAP_ENABLED",
            "GALAXY_CONTAINER_SIGNING_SERVICE",
            "GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS",
            "GALAXY_LDAP_DISABLE_REFERRALS",
            "KEYCLOAK_URL",
            "ANSIBLE_BASE_JWT_VALIDATE_CERT",
            "ANSIBLE_BASE_JWT_KEY",
            "ANSIBLE_BASE_ROLES_REQUIRE_VIEW",
            "DYNACONF_AFTER_GET_HOOKS",
            "ANSIBLE_API_HOSTNAME",
            "ANSIBLE_CONTENT_HOSTNAME",
            "CONTENT_ORIGIN",
            "TOKEN_SERVER",
            "TOKEN_AUTH_DISABLED",
            "IS_CONNECTED_TO_RESOURCE_SERVER",
        ]
        settings_dict = settings.as_dict()
        data = {key: settings_dict.get(key, None) for key in keyset}

        # these might not be strings ...
        if data.get("DYNACONF_AFTER_GET_HOOKS") is not None:
            data["DYNACONF_AFTER_GET_HOOKS"] = \
                [str(func) for func in settings_dict["DYNACONF_AFTER_GET_HOOKS"]]

        return _private_response(data)
