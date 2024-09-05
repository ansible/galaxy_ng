from django.conf import settings
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from galaxy_ng.app.api import base as api_base


class SettingsView(api_base.APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        data = {}
        keyset = [
            "GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS",
            "GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD",
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
            "ALLOW_LOCAL_RESOURCE_MANAGEMENT",
            "ANSIBLE_BASE_ROLES_REQUIRE_VIEW",
            "DYNACONF_AFTER_GET_HOOKS",
            "ANSIBLE_API_HOSTNAME",
            "ANSIBLE_CONTENT_HOSTNAME",
            "CONTENT_ORIGIN",
            "TOKEN_SERVER",
            "TOKEN_AUTH_DISABLED",
        ]
        settings_dict = settings.as_dict()
        data = {key: settings_dict.get(key, None) for key in keyset}

        # these might not be strings ...
        if data.get("DYNACONF_AFTER_GET_HOOKS") is not None:
            data["DYNACONF_AFTER_GET_HOOKS"] = \
                [str(func) for func in settings_dict["DYNACONF_AFTER_GET_HOOKS"]]

        return Response(data)
