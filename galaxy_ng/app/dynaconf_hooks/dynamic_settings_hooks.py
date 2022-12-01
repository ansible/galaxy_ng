"""
This register a Dynaconf Hook at the get method that makes specific keys
to be looked up from cache falling back to the dabatase or original value.

Only keys defined in DYNAMIC_SETTINGS_SCHEMA will be looked up from cache/db.

NOTES:
    - Cache is updated when the database Setting model is updated via Django manager
    - Cache is a single hashmap named "GALAXY_SETTINGS" including all the dynamic key:value pairs
    - The whole data in cache needs to be loaded for every get because dynaconf performs merging
"""
import logging
from typing import Any, Dict
from dynaconf import Dynaconf, FormattingError
from dynaconf.hooking import Hook, HookValue, Action
from dynaconf.base import RESERVED_ATTRS, UPPER_DEFAULT_SETTINGS, Settings
from django.core.exceptions import AppRegistryNotReady
from django.db.utils import OperationalError
from django.apps import apps
from galaxy_ng.app.dynamic_settings import DYNAMIC_SETTINGS_SCHEMA


logger = logging.getLogger(__name__)


def get_settings_from_db():
    """Reads database and loads all settings.
    All keys must be set because values can be composed of multiple keys.
    """
    try:
        from galaxy_ng.app.models.config import Setting
        data = Setting.as_dict()
        return data
    except (AppRegistryNotReady, OperationalError):
        return {}


def cache_db_settings_hook(
    settings_dict: Dict,
    value: HookValue,
    key: str,
    *args, **kwargs
) -> Any:
    """Load specific settings from cached db.
    Tries to read data from Redis DB cache, fallback to a database query, then to existing value
    """
    # HERE: Dynaconf will pass a settings, instead of
    # a settings_dict, so no need to build this here below.
    settings = Settings()

    if apps.ready and key.upper() in DYNAMIC_SETTINGS_SCHEMA:
        # TODO: Build the settings object before passing to here
        reserved_keys = set(RESERVED_ATTRS + UPPER_DEFAULT_SETTINGS)
        allowed_keys = settings_dict.keys() - reserved_keys
        new = {
            k: v
            for k, v
            in settings_dict.items()
            if k in allowed_keys
        }
        settings.update(new, tomlfy=True)

        from galaxy_ng.app.tasks.settings_cache import get_settings_from_cache
        if (data := get_settings_from_cache()):
            loader_identifier = "settings_cache"
        else:
            loader_identifier = "settings_db"
            data = get_settings_from_db()

        try:
            settings.update(data, loader_identifier=loader_identifier, tomlfy=True)
        except FormattingError as exc:
            # Don't raise, but log error
            # TODO: Find a way to cast this error to the API when
            # validating the save of a new setting.
            logger.error("Error loading dynamic settings: %s", str(exc))

    return settings.get(key, value.value)


def configure_dynamic_settings(settings: Dynaconf) -> Dict[str, Any]:
    """Add a hook to settings lookup to load data from cached db"""
    data = {"_registered_hooks": {Action.AFTER_GET: [Hook(cache_db_settings_hook)]}}
    return data
