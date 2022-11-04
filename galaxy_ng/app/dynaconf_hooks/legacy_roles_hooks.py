from typing import Any, Dict
from dynaconf import Dynaconf


def configure_legacy_roles(settings: Dynaconf) -> Dict[str, Any]:
    """Set the feature flag for legacy roles from the setting"""
    data = {}
    legacy_roles = settings.get("GALAXY_ENABLE_LEGACY_ROLES", False)
    data["GALAXY_FEATURE_FLAGS__legacy_roles"] = legacy_roles
    return data
