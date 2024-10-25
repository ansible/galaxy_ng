"""
Model definitions for django-automated-logging.
"""
import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import (
    CharField,
    ForeignKey,
    CASCADE,
    TextField,
    SmallIntegerField,
    PositiveIntegerField,
    DurationField,
    GenericIPAddressField,
    PositiveSmallIntegerField,
)
from picklefield.fields import PickledObjectField

from automated_logging.helpers import Operation
from automated_logging.helpers.enums import (
    DjangoOperations,
    PastM2MOperationMap,
    ShortOperationMap,
)
from automated_logging.settings import dev


class BaseModel(models.Model):
    """BaseModel that is inherited from every model. Includes basic information."""

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Application(BaseModel):
    """
    Used to save from which application an event or model originates.
    This is used to group by application.

    The application name can be null,
    if the name is None, then the application is unknown.
    """

    name = CharField(max_length=255, null=True)

    class Meta:
        verbose_name = "Application"
        verbose_name_plural = "Applications"

    class LoggingIgnore:
        complete = True

    def __str__(self):
        return self.name or "Unknown"


class ModelMirror(BaseModel):
    """
    Used to mirror properties of models - this is used to preserve logs of
    models removed to make the logs independent of the presence of the model
    in the application.
    """

    name = CharField(max_length=255)
    application = ForeignKey(Application, on_delete=CASCADE)

    class Meta:
        verbose_name = "Model Mirror"
        verbose_name_plural = "Model Mirrors"

    class LoggingIgnore:
        complete = True

    def __str__(self):
        return self.name


class ModelField(BaseModel):
    """
    Used to mirror properties of model fields - this is used to preserve logs of
    models and fields that might be removed/modified and have them independent
    of the actual field.
    """

    name = CharField(max_length=255)

    mirror = ForeignKey(ModelMirror, on_delete=CASCADE)
    type = CharField(max_length=255)  # string of type

    class Meta:
        verbose_name = "Model Field"
        verbose_name_plural = "Model Fields"

    class LoggingIgnore:
        complete = True


class ModelEntry(BaseModel):
    """
    Used to mirror the evaluated model value (via repr) and primary key and
    to ensure the log integrity independent of presence of the entry.
    """

    mirror = ForeignKey(ModelMirror, on_delete=CASCADE)

    value = TextField()  # (repr)
    primary_key = TextField()

    class Meta:
        verbose_name = "Model Entry"
        verbose_name_plural = "Model Entries"

    class LoggingIgnore:
        complete = True

    def __str__(self) -> str:
        return f'{self.mirror.name}' f'(pk="{self.primary_key}", value="{self.value}")'

    def long(self) -> str:
        """
        long representation
        """

        return f'{self.mirror.application.name}.{self})'

    def short(self) -> str:
        """
        short representation
        """
        return f'{self.mirror.name}({self.primary_key})'


class ModelEvent(BaseModel):
    """
    Used to record model entry events, like modification, removal or adding of
    values or relationships.
    """

    operation = SmallIntegerField(
        validators=[MinValueValidator(-1), MaxValueValidator(1)],
        null=True,
        choices=DjangoOperations,
    )

    user = ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=CASCADE, null=True
    )  # maybe don't cascade?
    entry = ForeignKey(ModelEntry, on_delete=CASCADE)

    # modifications = None  # One2Many -> ModelModification
    # relationships = None  # One2Many -> ModelRelationship

    # v experimental, opt-in (pickled object)
    snapshot = PickledObjectField(null=True)
    performance = DurationField(null=True)

    class Meta:
        verbose_name = "Model Event"
        verbose_name_plural = "Model Events"

    class LoggingIgnore:
        complete = True


class ModelValueModification(BaseModel):
    """
    Used to record the model entry event modifications of simple values.

    The operation attribute can have 4 valid values:
    -1 (delete), 0 (modify), 1 (create), None (n/a)

    previous and current record the value change that happened.
    """

    operation = SmallIntegerField(
        validators=[MinValueValidator(-1), MaxValueValidator(1)],
        null=True,
        choices=DjangoOperations,
    )

    field = ForeignKey(ModelField, on_delete=CASCADE)

    previous = TextField(null=True)
    current = TextField(null=True)

    event = ForeignKey(ModelEvent, on_delete=CASCADE, related_name='modifications')

    class Meta:
        verbose_name = "Model Entry Event Value Modification"
        verbose_name_plural = "Model Entry Event Value Modifications"

    class LoggingIgnore:
        complete = True

    def __str__(self) -> str:
        return (
            f'[{self.field.mirror.application.name}:'
            f'{self.field.mirror.name}:'
            f'{self.field.name}] '
            f'{self.previous} -> {self.current}'
        )

    def short(self) -> str:
        """
        short representation analogue of __str__
        """
        operation = Operation(self.operation)
        shorthand = {v: k for k, v in ShortOperationMap.items()}[operation]

        return f'{shorthand}{self.field.name}'


class ModelRelationshipModification(BaseModel):
    """
    Used to record the model entry even modifications of relationships. (M2M, Foreign)


    The operation attribute can have 4 valid values:
    -1 (delete), 0 (modify), 1 (create), None (n/a)

    field is the field where the relationship changed (entry got added or removed)
    and model is the entry that got removed/added from the relationship.
    """

    operation = SmallIntegerField(
        validators=[MinValueValidator(-1), MaxValueValidator(1)],
        null=True,
        choices=DjangoOperations,
    )

    field = ForeignKey(ModelField, on_delete=CASCADE)
    entry = ForeignKey(ModelEntry, on_delete=CASCADE)

    event = ForeignKey(ModelEvent, on_delete=CASCADE, related_name='relationships')

    class Meta:
        verbose_name = "Model Entry Event Relationship Modification"
        verbose_name_plural = "Model Entry Event Relationship Modifications"

    class LoggingIgnore:
        complete = True

    def __str__(self) -> str:
        operation = Operation(self.operation)
        past = {v: k for k, v in PastM2MOperationMap.items()}[operation]

        return (
            f'[{self.field.mirror.application}:'
            f'{self.field.mirror.name}:'
            f'{self.field.name}] '
            f'{past} {self.entry}'
        )

    def short(self) -> str:
        """
        short representation
        """
        operation = Operation(self.operation)
        shorthand = {v: k for k, v in ShortOperationMap.items()}[operation]
        return f'{shorthand}{self.entry.short()}'

    def medium(self) -> [str, str]:
        """
        short representation analogue of __str__ with additional field context
        :return:
        """
        operation = Operation(self.operation)
        shorthand = {v: k for k, v in ShortOperationMap.items()}[operation]

        return f'{shorthand}{self.field.name}', f'{self.entry.short()}'


class RequestContext(BaseModel):
    """
    Used to record contents of request and responses and their type.
    """

    content = PickledObjectField(null=True)
    type = CharField(max_length=255)

    class LoggingIgnore:
        complete = True


class RequestEvent(BaseModel):
    """
    Used to record events of requests that happened.

    uri is the accessed path and data is the data that was being transmitted
    and is opt-in for collection.

    status and method are their respective HTTP equivalents.
    """

    user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, null=True)

    # to mitigate "max_length"
    uri = TextField()

    request = ForeignKey(
        RequestContext, on_delete=CASCADE, null=True, related_name='request_context'
    )
    response = ForeignKey(
        RequestContext, on_delete=CASCADE, null=True, related_name='response_context'
    )

    status = PositiveSmallIntegerField()
    method = CharField(max_length=32)

    application = ForeignKey(Application, on_delete=CASCADE)

    ip = GenericIPAddressField(null=True)

    class Meta:
        verbose_name = "Request Event"
        verbose_name_plural = "Request Events"

    class LoggingIgnore:
        complete = True


class UnspecifiedEvent(BaseModel):
    """
    Used to record unspecified internal events that are dispatched via
    the python logging library. saves the message, level, line, file and application.
    """

    message = TextField(null=True)
    level = PositiveIntegerField(default=20)

    line = PositiveIntegerField(null=True)
    file = TextField(null=True)

    application = ForeignKey(Application, on_delete=CASCADE)

    class Meta:
        verbose_name = "Unspecified Event"
        verbose_name_plural = "Unspecified Events"

    class LoggingIgnore:
        complete = True


if dev:
    # if in development mode (set when testing or development)
    # import extra models
    from automated_logging.tests.models import *
