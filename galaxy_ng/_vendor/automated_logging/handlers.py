import re
from collections import OrderedDict
from datetime import timedelta
from logging import Handler, LogRecord
from pathlib import Path
from threading import Thread
from typing import Dict, Any, TYPE_CHECKING, List, Optional, Union, Type, Tuple

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.db.models import ForeignObject, Model


if TYPE_CHECKING:
    # we need to do this, to avoid circular imports
    from automated_logging.models import (
        RequestEvent,
        ModelEvent,
        ModelValueModification,
        ModelRelationshipModification,
    )


class DatabaseHandler(Handler):
    def __init__(
        self, *args, batch: Optional[int] = 1, threading: bool = False, **kwargs
    ):
        self.limit = batch or 1
        self.threading = threading
        self.instances = OrderedDict()
        super(DatabaseHandler, self).__init__(*args, **kwargs)

    @staticmethod
    def _clear(config):
        from automated_logging.models import ModelEvent, RequestEvent, UnspecifiedEvent
        from django.db import transaction

        current = timezone.now()
        with transaction.atomic():
            if config.model.max_age:
                ModelEvent.objects.filter(
                    created_at__lte=current - config.model.max_age
                ).delete()
            if config.unspecified.max_age:
                UnspecifiedEvent.objects.filter(
                    created_at__lte=current - config.unspecified.max_age
                ).delete()

            if config.request.max_age:
                RequestEvent.objects.filter(
                    created_at__lte=current - config.request.max_age
                ).delete()

    def save(self, instance=None, commit=True, clear=True):
        """
        Internal save procedure.
        Handles deletion when an event exceeds max_age
        and batch saving via atomic transactions.

        :return: None
        """
        from django.db import transaction
        from automated_logging.settings import settings

        if instance:
            self.instances[instance.pk] = instance
        if len(self.instances) < self.limit:
            if clear:
                self._clear(settings)
            return instance

        if not commit:
            return instance

        def database(instances, config):
            """ wrapper so that we can actually use threading """
            with transaction.atomic():
                [i.save() for k, i in instances.items()]

                if clear:
                    self._clear(config)
                instances.clear()

        if self.threading:
            thread = Thread(
                group=None, target=database, args=(self.instances, settings)
            )
            thread.start()
        else:
            database(self.instances, settings)

        return instance

    def get_or_create(self, target: Type[Model], **kwargs) -> Tuple[Model, bool]:
        """
        proxy for "get_or_create" from django,
        instead of creating it immediately we
        dd it to the list of objects to be created in a single swoop

        :type target: Model to be get_or_create
        :type kwargs: properties to be used to find and create the new object
        """
        created = False
        try:
            instance = target.objects.get(**kwargs)
        except ObjectDoesNotExist:
            instance = target(**kwargs)
            self.save(instance, commit=False, clear=False)
            created = True

        return instance, created

    def prepare_save(self, instance: Model):
        """
        Due to the nature of all modifications and such there are some models
        that are in nature get_or_create and not creations
        (we don't want so much additional data)

        This is a recursive function that looks for relationships and
        replaces specific values with their get_or_create counterparts.

        :param instance: model
        :return: instance that is suitable for saving
        """
        from automated_logging.models import (
            Application,
            ModelMirror,
            ModelField,
            ModelEntry,
        )

        if isinstance(instance, Application):
            return Application.objects.get_or_create(name=instance.name)[0]
        elif isinstance(instance, ModelMirror):
            return self.get_or_create(
                ModelMirror,
                name=instance.name,
                application=self.prepare_save(instance.application),
            )[0]
        elif isinstance(instance, ModelField):
            entry, _ = self.get_or_create(
                ModelField,
                name=instance.name,
                mirror=self.prepare_save(instance.mirror),
            )
            if entry.type != instance.type:
                entry.type = instance.type
                self.save(entry, commit=False, clear=False)
            return entry

        elif isinstance(instance, ModelEntry):
            entry, _ = self.get_or_create(
                ModelEntry,
                mirror=self.prepare_save(instance.mirror),
                primary_key=instance.primary_key,
            )
            if entry.value != instance.value:
                entry.value = instance.value
                self.save(entry, commit=False, clear=False)
            return entry

        # ForeignObjectRel is untouched rn
        for field in [
            f
            for f in instance._meta.get_fields()
            if isinstance(f, ForeignObject)
            and getattr(instance, f.name, None) is not None
            # check the attribute module really being automated_logging
            # to make sure that we do not follow down a rabbit hole
            and getattr(instance, f.name).__class__.__module__.split('.', 1)[0]
            == 'automated_logging'
        ]:
            setattr(
                instance, field.name, self.prepare_save(getattr(instance, field.name))
            )

        self.save(instance, commit=False, clear=False)
        return instance

    def unspecified(self, record: LogRecord) -> None:
        """
        This is for messages that are not sent from django-automated-logging.
        The option to still save these log messages is there. We create
        the event in the handler and then save them.

        :param record:
        :return:
        """
        from automated_logging.models import UnspecifiedEvent, Application
        from automated_logging.signals import unspecified_exclusion
        from django.apps import apps

        event = UnspecifiedEvent()
        if hasattr(record, 'message'):
            event.message = record.message
        event.level = record.levelno
        event.line = record.lineno
        event.file = Path(record.pathname)

        # this is semi-reliable, but I am unsure of a better way to do this.
        applications = apps.app_configs.keys()
        path = Path(record.pathname)
        candidates = [p for p in path.parts if p in applications]
        if candidates:
            # use the last candidate (closest to file)
            event.application = Application(name=candidates[-1])
        elif record.module in applications:
            # if we cannot find the application, we use the module as application
            event.application = Application(name=record.module)
        else:
            # if we cannot determine the application from the application
            # or from the module we presume that the application is unknown
            event.application = Application(name=None)

        if not unspecified_exclusion(event):
            self.prepare_save(event)
            self.save(event)

    def model(
        self,
        record: LogRecord,
        event: 'ModelEvent',
        modifications: List['ModelValueModification'],
        data: Dict[str, Any],
    ) -> None:
        """
        This is for model specific logging events.
        Compiles the information into an event and saves that event
        and all modifications done.

        :param event:
        :param modifications:
        :param record:
        :param data:
        :return:
        """
        self.prepare_save(event)
        self.save(event)

        for modification in modifications:
            modification.event = event
            self.prepare_save(modification)
            self.save()

    def m2m(
        self,
        record: LogRecord,
        event: 'ModelEvent',
        relationships: List['ModelRelationshipModification'],
        data: Dict[str, Any],
    ) -> None:
        self.prepare_save(event)
        self.save(event)

        for relationship in relationships:
            relationship.event = event
            self.prepare_save(relationship)
            self.save(relationship)

    def request(self, record: LogRecord, event: 'RequestEvent') -> None:
        """
        The request event already has a model prepared that we just
        need to prepare and save.

        :param record: LogRecord
        :param event: Event supplied via the LogRecord
        :return: nothing
        """

        self.prepare_save(event)
        self.save(event)

    def emit(self, record: LogRecord) -> None:
        """
        Emit function that gets triggered for every log message in scope.

        The record will be processed according to the action set.
        :param record:
        :return:
        """
        if not hasattr(record, 'action'):
            return self.unspecified(record)

        if record.action == 'model':
            return self.model(record, record.event, record.modifications, record.data)
        elif record.action == 'model[m2m]':
            return self.m2m(record, record.event, record.relationships, record.data)
        elif record.action == 'request':
            return self.request(record, record.event)
