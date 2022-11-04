from typing import Any, Dict
from dynaconf import Dynaconf

from .dynamic_settings_hooks import configure_dynamic_settings
from .ldap_hooks import configure_ldap
from .logging_hooks import configure_logging
from .keycloak_hooks import configure_keycloak
from .social_auth_hooks import configure_socialauth
from .cors_hooks import configure_cors
from .pulp_ansible_hooks import configure_pulp_ansible
from .authentication_hooks import (
    configure_authentication_classes,
    configure_authentication_backends,
    configure_password_validators,
)
from .api_base_path_hooks import configure_api_base_path
from .legacy_roles_hooks import configure_legacy_roles
from .validation import validate


def post(settings: Dynaconf) -> Dict[str, Any]:
    """The dynaconf post hook is called after all the settings are loaded and set.

    Post hook is necessary when a setting key depends conditionally on a previouslys et variable.

    settings: A read-only copy of the django.conf.settings
    returns: a dictionary to be merged to django.conf.settings

    NOTES:
        Feature flags must be loaded directly on `app/api/ui/views/feature_flags.py` view.
    """
    data = {"dynaconf_merge": False}
    # existing keys will be merged if dynaconf_merge is set to True
    # here it is set to false, so it allows each value to be individually marked as a merge.

    data.update(configure_ldap(settings))
    data.update(configure_logging(settings))
    data.update(configure_keycloak(settings))
    data.update(configure_socialauth(settings))
    data.update(configure_cors(settings))
    data.update(configure_pulp_ansible(settings))
    data.update(configure_authentication_backends(settings))
    data.update(configure_password_validators(settings))
    data.update(configure_api_base_path(settings))
    data.update(configure_legacy_roles(settings))

    # This should go last, and it needs to receive the data from the previous configuration
    # functions because this function configures the rest framework auth classes based off
    # of the galaxy auth classes, and if galaxy auth classes are overridden by any of the
    # other dynaconf hooks (such as keycloak), those changes need to be applied to the
    # rest framework auth classes too.
    data.update(configure_authentication_classes(settings, data))

    # This must go last, so that all the default settings are loaded before dynamic and validation
    data.update(configure_dynamic_settings(settings))
    validate(settings)
    return data
