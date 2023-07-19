import uuid
from django.db.models import (
    Model,
    UUIDField,
    DateTimeField,
    ManyToManyField,
    CASCADE,
    ForeignKey,
    OneToOneField,
    CharField,
)

from automated_logging.decorators import exclude_model, include_model


class TestBase(Model):
    """ Base for all the test models """

    id = UUIDField(default=uuid.uuid4, primary_key=True)

    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        app_label = 'automated_logging'


class OrdinaryBaseTest(TestBase):
    """ Ordinary base test. Has a random char field."""

    random = CharField(max_length=255, null=True)
    random2 = CharField(max_length=255, null=True)

    class Meta:
        abstract = True
        app_label = 'automated_logging'


class OrdinaryTest(OrdinaryBaseTest):
    """ Ordinary test. Has a random char field."""

    class Meta:
        app_label = 'automated_logging'


class M2MTest(TestBase):
    """ Used to test the Many-To-Many Relationship functionality of DAL"""

    relationship = ManyToManyField(OrdinaryTest)

    class Meta:
        app_label = 'automated_logging'


class ForeignKeyTest(TestBase):
    """ Used to test ForeignKey functionality of DAL."""

    relationship = ForeignKey(OrdinaryTest, on_delete=CASCADE, null=True)

    class Meta:
        app_label = 'automated_logging'


class OneToOneTest(TestBase):
    """ Used to test the One-To-One Relationship functionality of DAL."""

    relationship = OneToOneField(OrdinaryTest, on_delete=CASCADE, null=True)

    class Meta:
        app_label = 'automated_logging'


class SpeedTest(TestBase):
    """ Used to test the speed of DAL """

    for idx in range(100):
        exec(f"column{idx} = CharField(max_length=15, null=True)")

    class Meta:
        app_label = 'automated_logging'


class FullClassBasedExclusionTest(OrdinaryBaseTest):
    """ Used to test the full model exclusion via meta class"""

    class Meta:
        app_label = 'automated_logging'

    class LoggingIgnore:
        complete = True


class PartialClassBasedExclusionTest(OrdinaryBaseTest):
    """ Used to test partial ignore via fields """

    class Meta:
        app_label = 'automated_logging'

    class LoggingIgnore:
        fields = ['random']
        operations = ['delete']


@exclude_model
class FullDecoratorBasedExclusionTest(OrdinaryBaseTest):
    """ Used to test full decorator exclusion """

    class Meta:
        app_label = 'automated_logging'


@exclude_model(operations=['delete'], fields=['random'])
class PartialDecoratorBasedExclusionTest(OrdinaryBaseTest):
    """ Used to test partial decorator exclusion """

    class Meta:
        app_label = 'automated_logging'


@include_model
class DecoratorOverrideExclusionTest(OrdinaryBaseTest):
    """
    Used to check if include_model
    has precedence over class based configuration
    """

    class Meta:
        app_label = 'automated_logging'

    class LoggingIgnore:
        complete = True
