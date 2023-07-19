"""
Helper functions that are specifically used in the signals only.
"""

import re
from fnmatch import fnmatch
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Callable, Any

from automated_logging.helpers import (
    get_or_create_meta,
    get_or_create_thread,
    function2path,
    Operation,
)
from automated_logging.models import RequestEvent, UnspecifiedEvent
import automated_logging.decorators
from automated_logging.settings import settings
from automated_logging.helpers.schemas import Search


# suboptimal meta is also cached -> look into how to solve
@lru_cache()
def cached_model_exclusion(sender, meta, operation) -> bool:
    """ cached so that we don't need to abuse ._meta and can invalidate the cache """
    return model_exclusion(sender, meta, operation)


def lazy_model_exclusion(instance, operation, sender) -> bool:
    """
    First look if the model has been excluded already
    -> only then look if excluded.

    Replaced by LRU-Cache.
    """

    return cached_model_exclusion(sender, instance._meta, operation)


def candidate_in_scope(candidate: str, scope: List[Search]) -> bool:
    """
    Check if the candidate string is valid with the scope supplied,
    the scope should be list of search strings - that can be either
    glob, plain or regex

    :param candidate: search string
    :param scope: List of Search
    :return: valid?
    """

    for search in scope:
        match = False
        if search.type == 'glob':
            match = fnmatch(candidate.lower(), search.value.lower())
        if search.type == 'plain':
            match = candidate.lower() == search.value.lower()
        if search.type == 'regex':
            match = bool(re.match(search.value, candidate, re.IGNORECASE))

        if match:
            return True

    return False


def request_exclusion(event: RequestEvent, view: Optional[Callable] = None) -> bool:
    """
    Determine if a request should be ignored/excluded from getting
    logged, these exclusions should be specified in the settings.

    :param event: RequestEvent
    :param view: Optional - function used by the resolver
    :return: should be excluded?
    """

    if view:
        thread, _ = get_or_create_thread()
        ignore = thread.dal['ignore.views']
        include = thread.dal['include.views']
        path = function2path(view)

        # if include None or method in include return False and don't
        # check further, else just continue with checking
        if path in include and (include[path] is None or event.method in include[path]):
            return False

        if (
            path in ignore
            # if ignored[compiled] is None, then no method will be ignored
            and ignore[path] is not None
            # ignored[compiled] == [] indicates all should be ignored
            and (len(ignore[path]) == 0 or event.method in ignore[path])
        ):
            return True

    exclusions = settings.request.exclude
    if event.method.lower() in exclusions.methods:
        return True

    if event.application.name and candidate_in_scope(
        event.application.name, exclusions.applications
    ):
        return True

    if event.status in exclusions.status:
        return True

    # if the application.name = None, then the application is unknown.
    # exclusions.unknown specifies if unknown should be excluded!
    if not event.application.name and exclusions.unknown:
        return True

    return False


def _function_model_exclusion(sender, scope: str, item: Any) -> Optional[bool]:
    if not sender:
        return None

    thread, _ = get_or_create_thread()

    # noinspection PyProtectedMember
    ignore = automated_logging.decorators._exclude_models
    # noinspection PyProtectedMember
    include = automated_logging.decorators._include_models

    path = function2path(sender)

    if path in include:
        items = getattr(include[path], scope)
        if items is None or item in items:
            return False

    if path in ignore:
        items = getattr(ignore[path], scope)
        if items is not None and (len(items) == 0 or item in items):
            return True

    return None


def model_exclusion(sender, meta, operation: Operation) -> bool:
    """
    Determine if the instance of a model should be excluded,
    these exclusions should be specified in the settings.

    :param meta:
    :param sender:
    :param operation:
    :return: should be excluded?
    """
    decorators = _function_model_exclusion(sender, 'operations', operation)
    if decorators is not None:
        return decorators

    if hasattr(sender, 'LoggingIgnore') and (
        getattr(sender.LoggingIgnore, 'complete', False)
        or {
            Operation.CREATE: 'create',
            Operation.MODIFY: 'modify',
            Operation.DELETE: 'delete',
        }[operation]
        in [o.lower() for o in getattr(sender.LoggingIgnore, 'operations', [])]
    ):
        return True

    exclusions = settings.model.exclude
    module = sender.__module__
    name = sender.__name__
    application = meta.app_label

    if (
        candidate_in_scope(name, exclusions.models)
        or candidate_in_scope(f'{module}.{name}', exclusions.models)
        or candidate_in_scope(f'{application}.{name}', exclusions.models)
    ):
        return True

    if candidate_in_scope(module, exclusions.models):
        return True

    if application and candidate_in_scope(application, exclusions.applications):
        return True

    # if there is no application string then we assume the model
    # location is unknown, if the flag exclude.unknown = True, then we just exclude
    if not application and exclusions.unknown:
        return True

    return False


def field_exclusion(field: str, instance, sender=None) -> bool:
    """
    Determine if the field of an instance should be excluded.
    """

    decorators = _function_model_exclusion(sender, 'fields', field)
    if decorators is not None:
        return decorators

    if hasattr(instance.__class__, 'LoggingIgnore') and (
        getattr(instance.__class__.LoggingIgnore, 'complete', False)
        or field in getattr(instance.__class__.LoggingIgnore, 'fields', [])
    ):
        return True

    exclusions = settings.model.exclude
    application = instance._meta.app_label
    model = instance.__class__.__name__

    if (
        candidate_in_scope(field, exclusions.fields)
        or candidate_in_scope(f'{model}.{field}', exclusions.fields)
        or candidate_in_scope(f'{application}.{model}.{field}', exclusions.fields)
    ):
        return True

    return False


def unspecified_exclusion(event: UnspecifiedEvent) -> bool:
    """
    Determine if an unspecified event needs to be excluded.
    """
    exclusions = settings.unspecified.exclude

    if event.application.name and candidate_in_scope(
        event.application.name, exclusions.applications
    ):
        return True

    if candidate_in_scope(str(event.file), exclusions.files):
        return True

    path = Path(event.file)
    # match greedily by first trying the complete path, if that doesn't match try
    # full relative and then complete relative.
    if [
        v
        for v in exclusions.files
        if v.type != 'regex'
        and (
            path.match(v.value)
            or path.match(f'/*{v.value}')
            or fnmatch(path, f'{v.value}/*')
            or fnmatch(path, f'/*{v.value}')
            or fnmatch(path, f'/*{v.value}/*')
        )
    ]:
        return True

    # application.name = None and exclusion.unknown = True
    if not event.application.name and exclusions.unknown:
        return True

    return False
