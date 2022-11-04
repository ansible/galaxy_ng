from typing import Any, Dict
from dynaconf import Dynaconf
from dynaconf.hooking import Hook, HookValue, Action
# from galaxy_ng.app.dynamic_settings import ROUTED_KEYS


FAKE_DB = {
    'GALAXY_REQUIRE_CONTENT_APPROVAL': False,
    'GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL': False,
    'GALAXY_SIGNATURE_UPLOAD_ENABLED': False,
    'GALAXY_AUTO_SIGN_COLLECTIONS': False,
    'GALAXY_FEATURE_FLAGS': {}
}


def get_from_cache_or_db_default(
    settings: Dynaconf,
    value: HookValue,
    key: str,
    *args, **kwargs
) -> Any:
    """Load specific settings from cached db.
    Tries to read data from Redis DB cache, fallback to a database query, then to existing value
    """
    settings.update(FAKE_DB, loader_identifier="db_cache_loader")
    return settings.get(key, value.value), args, kwargs


def configure_dynamic_settings(settings: Dynaconf) -> Dict[str, Any]:
    """Add a hook to settings lookup to load data from cached db"""
    data = {"_registered_hooks": {Action.AFTER_GET: [Hook(get_from_cache_or_db_default)]}}
    return data
