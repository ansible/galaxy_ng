import json
import os
import sys
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    KEYCLOAK_KEYS = [
        "SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL",
        "SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL",
        "SOCIAL_AUTH_KEYCLOAK_KEY",
        "SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY",
        "SOCIAL_AUTH_KEYCLOAK_SECRET",
    ]

    LDAP_KEYS = [
        "AUTH_LDAP_SERVER_URI",
        "AUTH_LDAP_BIND_DN",
        "AUTH_LDAP_BIND_PASSWORD",
        "AUTH_LDAP_USER_SEARCH_BASE_DN",
        "AUTH_LDAP_USER_SEARCH_SCOPE",
        "AUTH_LDAP_USER_SEARCH_FILTER",
        "AUTH_LDAP_GROUP_SEARCH_BASE_DN",
        "AUTH_LDAP_GROUP_SEARCH_SCOPE",
        "AUTH_LDAP_GROUP_SEARCH_FILTER",
    ]

    help = "Dump auth config data from database to a JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "output_file",
            nargs="?",
            type=str,
            default=None,
            help="Output JSON file path",
        )

    def is_enabled(self, keys):
        values = []
        for key in keys:
            values.append(settings.get(key, default=None))
        return all(values)

    def post_config_ldap(self):
        post_config = {}
        # Other required platform params
        post_config["USER_ATTR_MAP"] = settings.get("AUTH_LDAP_USER_ATTR_MAP")
        post_config["USER_DN_TEMPLATE"] = settings.get("AUTH_LDAP_USER_DN_TEMPLATE")
        post_config["GROUP_TYPE_PARAMS"] = settings.get("AUTH_LDAP_GROUP_TYPE_PARAMS")
        post_config["CONNECTION_OPTIONS"] = settings.get("AUTH_LDAP_CONNECTION_OPTIONS")
        post_config["START_TLS"] = settings.get("AUTH_LDAP_START_TLS")

        # Configure USER_SEARCH and GROUP_SEARCH
        AUTH_LDAP_USER_SEARCH_BASE_DN = settings.get("AUTH_LDAP_USER_SEARCH_BASE_DN", default=None)
        AUTH_LDAP_USER_SEARCH_SCOPE = settings.get("AUTH_LDAP_USER_SEARCH_SCOPE", default=None)
        AUTH_LDAP_USER_SEARCH_FILTER = settings.get("AUTH_LDAP_USER_SEARCH_FILTER", default=None)
        AUTH_LDAP_GROUP_SEARCH_BASE_DN = settings.get(
            "AUTH_LDAP_GROUP_SEARCH_BASE_DN",
            default=None
        )
        AUTH_LDAP_GROUP_SEARCH_SCOPE = settings.get("AUTH_LDAP_GROUP_SEARCH_SCOPE", default=None)
        AUTH_LDAP_GROUP_SEARCH_FILTER = settings.get("AUTH_LDAP_GROUP_SEARCH_FILTER", default=None)

        post_config["USER_SEARCH"] = [
            AUTH_LDAP_USER_SEARCH_BASE_DN,
            AUTH_LDAP_USER_SEARCH_SCOPE,
            AUTH_LDAP_USER_SEARCH_FILTER,
        ]

        post_config["GROUP_SEARCH"] = [
            AUTH_LDAP_GROUP_SEARCH_BASE_DN,
            AUTH_LDAP_GROUP_SEARCH_SCOPE,
            AUTH_LDAP_GROUP_SEARCH_FILTER,
        ]

        # Configure GROUP_TYPE
        post_config["GROUP_TYPE"] = None
        AUTH_LDAP_GROUP_TYPE = settings.get("AUTH_LDAP_GROUP_TYPE")
        if AUTH_LDAP_GROUP_TYPE:
            post_config["GROUP_TYPE"] = type(AUTH_LDAP_GROUP_TYPE).__name__

        return post_config

    def format_config_data(self, type, keys, prefix):
        config = {
            "type": f"galaxy.authentication.authenticator_plugins.{type}",
            "enabled": self.is_enabled(keys),
            "configuration": {},
        }
        for key in keys:
            k = key
            if prefix in key:
                k = key[len(prefix):]
            v = settings.get(key, default=None)
            config["configuration"].update({k: v})

        # handle post configuration for ldap:
        if type == "ldap":
            config["configuration"].update(self.post_config_ldap())

        return config

    def handle(self, *args, **options):
        try:
            data = []

            # Add Keycloak auth config
            data.append(
                self.format_config_data(
                    "keycloak",
                    self.KEYCLOAK_KEYS,
                    "SOCIAL_AUTH_KEYCLOAK_"),
            )

            # Add LDAP auth config
            data.append(self.format_config_data("ldap", self.LDAP_KEYS, "AUTH_LDAP_"))

            # write to file if requested
            if options["output_file"]:
                # Define the path for the output JSON file
                output_file = options["output_file"]

                # Ensure the directory exists
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

                # Write data to the JSON file
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=4)

                self.stdout.write(
                    self.style.SUCCESS(f"Auth config data dumped to {output_file}")
                )
            else:
                self.stdout.write(json.dumps(data))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
            sys.exit(1)
