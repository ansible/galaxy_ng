from typing import Any, Dict, List
from dynaconf import Dynaconf


def configure_authentication_backends(settings: Dynaconf) -> Dict[str, Any]:
    """Configure authentication backends for galaxy.
    This function returns a dictionary that will be merged to the settings.
    """
    data = {}

    choosen_preset = settings.get("AUTHENTICATION_BACKEND_PRESET")
    # If `custom` it will allow user to override and not raise Validation Error
    # If `local` it will not be set and will use the default coming from pulp

    presets = settings.get("AUTHENTICATION_BACKEND_PRESETS_DATA", {})
    if choosen_preset in presets:
        data["AUTHENTICATION_BACKENDS"] = presets[choosen_preset]

    return data


def configure_authentication_classes(settings: Dynaconf, data: Dict[str, Any]) -> Dict[str, Any]:
    # GALAXY_AUTHENTICATION_CLASSES is used to configure the galaxy api authentication
    # pretty much everywhere (on prem, cloud, dev environments, CI environments etc).
    # We need to set the REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES variable so that
    # the pulp APIs use the same authentication as the galaxy APIs. Rather than setting
    # the galaxy auth classes and the DRF classes in all those environments just set the
    # default rest framework auth classes to the galaxy auth classes. Ideally we should
    # switch everything to use the default DRF auth classes, but given how many
    # environments would have to be reconfigured, this is a lot easier.
    galaxy_auth_classes = data.get(
        "GALAXY_AUTHENTICATION_CLASSES",
        settings.get("GALAXY_AUTHENTICATION_CLASSES", None)
    )

    if galaxy_auth_classes:
        return {
            "REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES": galaxy_auth_classes
        }
    else:
        return {}


def configure_password_validators(settings: Dynaconf) -> Dict[str, Any]:
    """Configure the password validators"""
    GALAXY_MINIMUM_PASSWORD_LENGTH: int = settings.get("GALAXY_MINIMUM_PASSWORD_LENGTH", 9)
    AUTH_PASSWORD_VALIDATORS: List[Dict[str, Any]] = settings.AUTH_PASSWORD_VALIDATORS
    # NOTE: Dynaconf can't add or merge on dicts inside lists.
    # So we need to traverse the list to change it until the RFC is implemented
    # https://github.com/rochacbruno/dynaconf/issues/299#issuecomment-900616706
    for dict_item in AUTH_PASSWORD_VALIDATORS:
        if dict_item["NAME"].endswith("MinimumLengthValidator"):
            dict_item["OPTIONS"]["min_length"] = int(GALAXY_MINIMUM_PASSWORD_LENGTH)
    return {"AUTH_PASSWORD_VALIDATORS": AUTH_PASSWORD_VALIDATORS}
