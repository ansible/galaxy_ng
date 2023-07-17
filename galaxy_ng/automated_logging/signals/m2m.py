"""
This module specifically handlers "many to many" changes, those are
a bit more complicated as we need to detect the changes
on a per field basis.

This finds the changes and redirects them to the handler,
without doing any changes to the database.
"""


import logging
from typing import Optional

from django.db.models import Manager
from django.db.models.fields.related import ManyToManyField
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from automated_logging.helpers import (
    Operation,
    get_or_create_model_event,
    get_or_create_meta,
)
from automated_logging.models import (
    ModelRelationshipModification,
    ModelEntry,
    ModelMirror,
    Application,
    ModelField,
)
from automated_logging.settings import settings
from automated_logging.signals import lazy_model_exclusion

logger = logging.getLogger(__name__)


def find_m2m_rel(sender, model) -> Optional[ManyToManyField]:
    """
    This finds the "many to many" relationship that is used by the sender.
    """
    for field in model._meta.get_fields():
        if isinstance(field, ManyToManyField) and field.remote_field.through == sender:
            return field

    return None


def post_processor(sender, instance, model, operation, targets):
    """
    if the change is in reverse or not, the processing of the changes is still
    the same, so we have this method to take care of constructing the changes
    :param sender:
    :param instance:
    :param model:
    :param operation:
    :param targets:
    :return:
    """
    relationships = []

    m2m_rel = find_m2m_rel(sender, model)
    if not m2m_rel:
        logger.warning(f'[DAL] save[m2m] could not find ManyToManyField for {instance}')
        return

    field = ModelField()
    field.name = m2m_rel.name
    field.mirror = ModelMirror(
        name=model.__name__, application=Application(name=instance._meta.app_label)
    )
    field.type = m2m_rel.__class__.__name__

    # there is the possibility that a pre_clear occurred, if that is the case
    # extend the targets and pop the list of affected instances from the attached
    # field
    get_or_create_meta(instance)
    if (
        hasattr(instance._meta.dal, 'm2m_pre_clear')
        and field.name in instance._meta.dal.m2m_pre_clear
        and operation == Operation.DELETE
    ):
        cleared = instance._meta.dal.m2m_pre_clear[field.name]
        targets.extend(cleared)
        instance._meta.dal.m2m_pre_clear.pop(field.name)

    for target in targets:
        relationship = ModelRelationshipModification()
        relationship.operation = operation
        relationship.field = field
        mirror = ModelMirror()
        mirror.name = target.__class__.__name__
        mirror.application = Application(name=target._meta.app_label)
        relationship.entry = ModelEntry(
            mirror=mirror, value=repr(target), primary_key=target.pk
        )
        relationships.append(relationship)

    if len(relationships) == 0:
        # there was no actual change, so we're not propagating the event
        return

    event, _ = get_or_create_model_event(instance, operation)

    user = None
    logger.log(
        settings.model.loglevel,
        f'{user or "Anonymous"} modified field '
        f'{field.name} | Model: '
        f'{field.mirror.application}.{field.mirror} '
        f'| Modifications: {", ".join([r.short() for r in relationships])}',
        extra={
            'action': 'model[m2m]',
            'data': {'instance': instance, 'sender': sender},
            'relationships': relationships,
            'event': event,
        },
    )


def pre_clear_processor(sender, instance, pks, model, reverse, operation) -> None:
    """
    pre_clear needs a specific processor as we attach the changes that are about
    to happen to the instance first, and then use them in post_delete/post_clear

    if reverse = False then every element gets removed from the relationship field,
    but if reverse = True then instance should be removed from every target.

    Note: it seems that pre_clear is not getting fired for reverse.

    :return: None
    """
    if reverse:
        return

    get_or_create_meta(instance)

    rel = find_m2m_rel(sender, instance.__class__)
    if 'm2m_pre_clear' not in instance._meta.dal:
        instance._meta.dal.m2m_pre_clear = {}

    cleared = getattr(instance, rel.name, [])
    if isinstance(cleared, Manager):
        cleared = list(cleared.all())
    instance._meta.dal.m2m_pre_clear = {rel.name: cleared}


@receiver(m2m_changed, weak=False)
def m2m_changed_signal(
    sender, instance, action, reverse, model, pk_set, using, **kwargs
) -> None:
    """
    Django sends this signal when many-to-many relationships change.

    One of the more complex signals, due to the fact that change can be reversed
    we need to either process
    instance field changes of pk_set (reverse=False) or
    pk_set field changes of instance. (reverse=True)

    The changes will always get applied in the model where the field in defined.

    # TODO: post_remove also gets triggered when there is nothing actually getting removed
    :return: None
    """
    if action not in ['post_add', 'post_remove', 'pre_clear', 'post_clear']:
        return

    if action == 'pre_clear':
        operation = Operation.DELETE

        return pre_clear_processor(
            sender,
            instance,
            list(pk_set) if pk_set else None,
            model,
            reverse,
            operation,
        )
    elif action == 'post_add':
        operation = Operation.CREATE
    elif action == 'post_clear':
        operation = Operation.DELETE
    else:
        operation = Operation.DELETE

    targets = model.objects.filter(pk__in=list(pk_set)) if pk_set else []
    if reverse:
        for target in [
            t for t in targets if not lazy_model_exclusion(t, operation, t.__class__)
        ]:
            post_processor(sender, target, target.__class__, operation, [instance])
    else:
        if lazy_model_exclusion(instance, operation, instance.__class__):
            return

        post_processor(sender, instance, instance.__class__, operation, targets)
