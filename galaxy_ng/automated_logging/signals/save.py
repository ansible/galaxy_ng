"""
File handles every signal related to the saving/deletion of django models.
"""

import logging
from collections import namedtuple
from datetime import datetime
from pprint import pprint
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from automated_logging.models import (
    ModelValueModification,
    ModelField,
    ModelMirror,
    Application,
)
from automated_logging.settings import settings
from automated_logging.signals import (
    model_exclusion,
    lazy_model_exclusion,
    field_exclusion,
)
from automated_logging.helpers import (
    get_or_create_meta,
    Operation,
    get_or_create_model_event,
)
from automated_logging.helpers.enums import PastOperationMap

ChangeSet = namedtuple('ChangeSet', ('deleted', 'added', 'changed'))
logger = logging.getLogger(__name__)


def normalize_save_value(value: Any):
    """ normalize the values given to the function to make stuff more readable """
    if value is None or value == '':
        return None
    if isinstance(value, str):
        return value

    return repr(value)


@receiver(pre_save, weak=False)
@transaction.atomic
def pre_save_signal(sender, instance, **kwargs) -> None:
    """
    Compares the current instance and old instance (fetched via the pk)
    and generates a dictionary of changes

    :param sender:
    :param instance:
    :param kwargs:
    :return: None
    """
    get_or_create_meta(instance)
    # clear the event to be sure
    instance._meta.dal.event = None

    operation = Operation.MODIFY
    try:
        pre = sender.objects.get(pk=instance.pk)
    except ObjectDoesNotExist:
        # __dict__ is used on pre, therefore we need to create a function
        # that uses __dict__ too, but returns nothing.

        pre = lambda _: None
        operation = Operation.CREATE

    excluded = lazy_model_exclusion(instance, operation, instance.__class__)
    if excluded:
        return

    old, new = pre.__dict__, instance.__dict__

    previously = set(
        k for k in old.keys() if not k.startswith('_') and old[k] is not None
    )
    currently = set(
        k for k in new.keys() if not k.startswith('_') and new[k] is not None
    )

    added = currently.difference(previously)
    deleted = previously.difference(currently)
    changed = {
        k
        for k in
        # take all keys from old and new, and only use those that are in both
        set(old.keys()) & set(new.keys())
        # remove values that have been added or deleted (optimization)
        .difference(added).difference(deleted)
        # check if the value is equal, if not they are not changed
        if old[k] != new[k]
    }

    summary = [
        *(
            {
                'operation': Operation.CREATE,
                'previous': None,
                'current': new[k],
                'key': k,
            }
            for k in added
        ),
        *(
            {
                'operation': Operation.DELETE,
                'previous': old[k],
                'current': None,
                'key': k,
            }
            for k in deleted
        ),
        *(
            {
                'operation': Operation.MODIFY,
                'previous': old[k],
                'current': new[k],
                'key': k,
            }
            for k in changed
        ),
    ]

    # exclude fields not present in _meta.get_fields
    fields = {f.name: f for f in instance._meta.get_fields()}
    extra = {f.attname: f for f in instance._meta.get_fields() if hasattr(f, 'attname')}
    fields = {**extra, **fields}

    summary = [s for s in summary if s['key'] in fields.keys()]

    # field exclusion
    summary = [
        s
        for s in summary
        if not field_exclusion(s['key'], instance, instance.__class__)
    ]

    model = ModelMirror()
    model.name = sender.__name__
    model.application = Application(name=instance._meta.app_label)

    modifications = []
    for entry in summary:
        field = ModelField()
        field.name = entry['key']
        field.mirror = model

        field.type = fields[entry['key']].__class__.__name__

        modification = ModelValueModification()
        modification.operation = entry['operation']
        modification.field = field

        modification.previous = normalize_save_value(entry['previous'])
        modification.current = normalize_save_value(entry['current'])

        modifications.append(modification)

    instance._meta.dal.modifications = modifications

    if settings.model.performance:
        instance._meta.dal.performance = datetime.now()


def post_processor(status, sender, instance, updated=None, suffix='') -> None:
    """
    Due to the fact that both post_delete and post_save have
    the same logic for propagating changes, we have this helper class
    to do so, just simply wraps and logs the data the handler needs.

    The event gets created here instead of the handler to keep
    everything consistent and have the handler as simple as possible.

    :param status: Operation
    :param sender: model class
    :param instance: model instance
    :param updated: updated fields
    :param suffix: suffix to be added to the message
    :return: None
    """
    past = {v: k for k, v in PastOperationMap.items()}

    get_or_create_meta(instance)

    event, _ = get_or_create_model_event(instance, status, force=True, extra=True)
    modifications = getattr(instance._meta.dal, 'modifications', [])

    # clear the modifications meta list
    instance._meta.dal.modifications = []

    if len(modifications) == 0 and status == Operation.MODIFY:
        # if the event is modify, but nothing changed, don't actually propagate
        return

    logger.log(
        settings.model.loglevel,
        f'{event.user or "Anonymous"} {past[status]} '
        f'{event.entry.mirror.application}.{sender.__name__} | '
        f'Instance: {instance!r}{suffix}',
        extra={
            'action': 'model',
            'data': {'status': status, 'instance': instance},
            'event': event,
            'modifications': modifications,
        },
    )


@receiver(post_save, weak=False)
@transaction.atomic
def post_save_signal(
    sender, instance, created, update_fields: frozenset, **kwargs
) -> None:
    """
    Signal is getting called after a save has been concluded. When this
    is the case we can be sure the save was successful and then only
    propagate the changes to the handler.

    :param sender: model class
    :param instance: model instance
    :param created: bool, was the model created?
    :param update_fields: which fields got explicitly updated?
    :param kwargs: django needs kwargs to be there
    :return: -
    """
    status = Operation.CREATE if created else Operation.MODIFY
    if lazy_model_exclusion(
        instance,
        status,
        instance.__class__,
    ):
        return
    get_or_create_meta(instance)

    suffix = f''
    if (
        status == Operation.MODIFY
        and hasattr(instance._meta.dal, 'modifications')
        and settings.model.detailed_message
    ):
        suffix = (
            f' | Modifications: '
            f'{", ".join([m.short() for m in instance._meta.dal.modifications])}'
        )

    if update_fields is not None and hasattr(instance._meta.dal, 'modifications'):
        instance._meta.dal.modifications = [
            m for m in instance._meta.dal.modifications if m.field.name in update_fields
        ]

    post_processor(status, sender, instance, update_fields, suffix)


@receiver(post_delete, weak=False)
@transaction.atomic
def post_delete_signal(sender, instance, **kwargs) -> None:
    """
    Signal is getting called after instance deletion. We just redirect the
    event to the post_processor.

    TODO: consider doing a "delete snapshot"

    :param sender: model class
    :param instance: model instance
    :param kwargs: required bt django
    :return: -
    """

    get_or_create_meta(instance)
    instance._meta.dal.event = None

    if lazy_model_exclusion(instance, Operation.DELETE, instance.__class__):
        return

    post_processor(Operation.DELETE, sender, instance)
