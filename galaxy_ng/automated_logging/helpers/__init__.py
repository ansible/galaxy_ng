"""
Helpers that are used throughout django-automated-logging
"""

from datetime import datetime
from typing import Any, Union, Dict, NamedTuple

from automated_logging.helpers.enums import Operation
from automated_logging.middleware import AutomatedLoggingMiddleware


def namedtuple2dict(root: Union[NamedTuple, Dict]) -> dict:
    """
    transforms nested namedtuple into a dict

    :param root: namedtuple to convert
    :return: dictionary from namedtuple
    """

    output = {}
    if (
        isinstance(root, tuple)
        and hasattr(root, '_serialize')
        and callable(root._serialize)
    ):
        return root._serialize()

    root = root if isinstance(root, dict) else root._asdict()

    def eligible(x):
        """ check if value x is eligible for recursion """
        return isinstance(x, tuple) or isinstance(x, dict)

    for k, v in root.items():
        if isinstance(v, set) or isinstance(v, list):
            output[k] = [namedtuple2dict(i) if eligible(i) else i for i in v]
        else:
            output[k] = namedtuple2dict(v) if eligible(v) else v

    return output


def get_or_create_meta(instance) -> [Any, bool]:
    """
    Simple helper function that creates the dal object
    in _meta.

    :param instance:
    :return:
    """
    return instance, get_or_create_local(instance._meta)


def get_or_create_thread() -> [Any, bool]:
    """
    Get or create the local thread, will always return False as the thread
    won't be created, but the local dal object will.

    get_or_create to conform with the other functions.

    :return: thread, created dal object?
    """
    thread = AutomatedLoggingMiddleware.thread

    return (
        thread,
        get_or_create_local(
            thread,
            {
                'ignore.views': dict,
                'ignore.models': dict,
                'include.views': dict,
                'include.models': dict,
            },
        ),
    )


def get_or_create_local(target: Any, defaults={}, key='dal') -> bool:
    """
    Get or create local storage DAL metadata container,
    where dal specific data is.

    :return: created?
    """

    if not hasattr(target, key):
        setattr(target, key, MetaDataContainer(defaults))
        return True

    return False


def get_or_create_model_event(
    instance, operation: Operation, force=False, extra=False
) -> [Any, bool]:
    """
    Get or create the ModelEvent of an instance.
    This function will also populate the event with the current information.

    :param instance: instance to derive an event from
    :param operation: specified operation that is done
    :param force: force creation of new event?
    :param extra: extra information inserted?
    :return: [event, created?]
    """
    from automated_logging.models import (
        ModelEvent,
        ModelEntry,
        ModelMirror,
        Application,
    )
    from automated_logging.settings import settings

    get_or_create_meta(instance)

    if hasattr(instance._meta.dal, 'event') and not force:
        return instance._meta.dal.event, False

    instance._meta.dal.event = None

    event = ModelEvent()
    event.user = AutomatedLoggingMiddleware.get_current_user()

    if settings.model.snapshot and extra:
        event.snapshot = instance

    if (
        settings.model.performance
        and hasattr(instance._meta.dal, 'performance')
        and extra
    ):
        event.performance = datetime.now() - instance._meta.dal.performance
        instance._meta.dal.performance = None

    event.operation = operation
    event.entry = ModelEntry()
    event.entry.mirror = ModelMirror()
    event.entry.mirror.name = instance.__class__.__name__
    event.entry.mirror.application = Application(name=instance._meta.app_label)
    event.entry.value = repr(instance) or str(instance)
    event.entry.primary_key = instance.pk

    instance._meta.dal.event = event

    return instance._meta.dal.event, True


def function2path(func):
    """ simple helper function to return the module path of a function """
    return f'{func.__module__}.{func.__name__}'


class MetaDataContainer(dict):
    """
    MetaDataContainer is used to store DAL specific metadata
    in various places.

    Values can be retrieved via attribute or key retrieval.

    A dictionary with key attributes can be provided when __init__.
    The key should be the name of the item, the value should be a function
    that gets called when an item with that key does
    not exist gets accessed, to auto-initialize that key.
    """

    def __init__(self, defaults={}):
        super().__init__()

        self.auto = defaults

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            if item in self.auto:
                self[item] = self.auto[item]()
                return self[item]
            else:
                raise KeyError

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError

    def __setattr__(self, key, value):
        self[key] = value
