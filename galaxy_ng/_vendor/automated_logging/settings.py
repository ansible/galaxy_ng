"""
Serialization of AUTOMATED_LOGGING_SETTINGS
"""

from collections import namedtuple
from functools import lru_cache
from logging import INFO, NOTSET, CRITICAL
from pprint import pprint

from marshmallow.fields import Boolean, Integer
from marshmallow.validate import OneOf, Range

from automated_logging.helpers.schemas import (
    Set,
    LowerCaseString,
    SearchString,
    MissingNested,
    BaseSchema,
    Search,
    Duration,
)


class RequestExcludeSchema(BaseSchema):
    """
    Configuration schema for request exclusion, that is only used in RequestSchema,
    is used to exclude unknown sources, applications, methods and status codes.
    """

    unknown = Boolean(missing=False)
    applications = Set(SearchString(), missing=set())

    methods = Set(LowerCaseString(), missing={'GET'})
    status = Set(Integer(validate=Range(min=0)), missing={200})


class RequestDataSchema(BaseSchema):
    """
    Configuration schema for request data that is only used in RequestSchema
    and is used to enable data collection, ignore keys that are going to be omitted
    mask keys (their value is going to be replaced with <REDACTED>)
    """

    enabled = Set(
        LowerCaseString(validate=OneOf(['request', 'response'])),
        missing=set(),
    )
    query = Boolean(missing=False)

    ignore = Set(LowerCaseString(), missing=set())
    mask = Set(LowerCaseString(), missing={'password'})

    # TODO: add more, change name?
    content_types = Set(
        LowerCaseString(validate=OneOf(['application/json'])),
        missing={'application/json'},
    )


class RequestSchema(BaseSchema):
    """
    Configuration schema for the request module.
    """

    loglevel = Integer(missing=INFO, validate=Range(min=NOTSET, max=CRITICAL))
    exclude = MissingNested(RequestExcludeSchema)

    data = MissingNested(RequestDataSchema)

    ip = Boolean(missing=True)
    # TODO: performance setting?

    log_request_was_not_recorded = Boolean(missing=True)
    max_age = Duration(missing=None)


class ModelExcludeSchema(BaseSchema):
    """
    Configuration schema, that is only used in ModelSchema and is used to
    exclude unknown sources, fields, models and applications.

    fields should be either <field> (every field that matches this name will be excluded),
    or <model>.<field>, or <application>.<model>.<field>

    models should be either <model> (every model regardless of module or application).
    <module> (python module location) or <module>.<model> (python module location)
    """

    unknown = Boolean(missing=False)
    fields = Set(SearchString(), missing=set())
    models = Set(SearchString(), missing=set())
    applications = Set(SearchString(), missing=set())


class ModelSchema(BaseSchema):
    """
    Configuration schema for the model module. mask property indicates
    which fields to specifically replace with <REDACTED>,
    this should be used for fields that are
    sensitive, but shouldn't be completely excluded.
    """

    loglevel = Integer(missing=INFO, validate=Range(min=NOTSET, max=CRITICAL))
    exclude = MissingNested(ModelExcludeSchema)

    # should the log message include all modifications done?
    detailed_message = Boolean(missing=True)

    # if execution_time should be measured of ModelEvent
    performance = Boolean(missing=False)
    snapshot = Boolean(missing=False)

    max_age = Duration(missing=None)


class UnspecifiedExcludeSchema(BaseSchema):
    """
    Configuration schema, that is only used in UnspecifiedSchema and defines
    the configuration settings to allow unknown sources, exclude files and
    specific Django applications
    """

    unknown = Boolean(missing=False)
    files = Set(SearchString(), missing=set())
    applications = Set(SearchString(), missing=set())


class UnspecifiedSchema(BaseSchema):
    """
    Configuration schema for the unspecified module.
    """

    loglevel = Integer(missing=INFO, validate=Range(min=NOTSET, max=CRITICAL))
    exclude = MissingNested(UnspecifiedExcludeSchema)

    max_age = Duration(missing=None)


class GlobalsExcludeSchema(BaseSchema):
    """
    Configuration schema, that is used for every single module.
    There are some packages where it is sensible to have the same
    exclusions.

    Things specified in globals will get appended to the other configurations.
    """

    applications = Set(
        SearchString(),
        missing={
            Search('glob', 'session*'),
            Search('plain', 'admin'),
            Search('plain', 'basehttp'),
            Search('plain', 'migrations'),
            Search('plain', 'contenttypes'),
        },
    )


class GlobalsSchema(BaseSchema):
    """
    Configuration schema for global, module unspecific configuration details.
    """

    exclude = MissingNested(GlobalsExcludeSchema)


class ConfigSchema(BaseSchema):
    """
    Skeleton configuration schema, that is used to enable/disable modules
    and includes the nested module configurations.
    """

    modules = Set(
        LowerCaseString(validate=OneOf(['request', 'model', 'unspecified'])),
        missing={'request', 'model', 'unspecified'},
    )

    request = MissingNested(RequestSchema)
    model = MissingNested(ModelSchema)
    unspecified = MissingNested(UnspecifiedSchema)

    globals = MissingNested(GlobalsSchema)


default: namedtuple = ConfigSchema().load({})


class Settings:
    """
    Settings wrapper,
    with the wrapper we can force lru_cache to be
    cleared on the specific instance
    """

    def __init__(self):
        self.loaded = None
        self.load()

    @lru_cache()
    def load(self):
        """
        loads settings from the schemes provided,
        done via function to utilize LRU cache
        """

        from django.conf import settings as st

        loaded: namedtuple = default

        if hasattr(st, 'AUTOMATED_LOGGING'):
            loaded = ConfigSchema().load(st.AUTOMATED_LOGGING)

        # be sure `loaded` has globals as we're working with those,
        # if that is not the case early return.
        if not hasattr(loaded, 'globals'):
            return loaded

        # use the binary **or** operator to apply globals to Set() attributes
        values = {}
        for name in loaded._fields:
            field = getattr(loaded, name)
            values[name] = field

            if not isinstance(field, tuple) or name == 'globals':
                continue

            values[name] = field | loaded.globals

        self.loaded = loaded._replace(**values)
        return self

    def __getattr__(self, item):
        # self.load() should only trigger when the cache is invalid
        self.load()

        return getattr(self.loaded, item)


@lru_cache()
def load_dev():
    """
    utilize LRU cache and local imports to always
    have an up to date version of the settings

    :return:
    """
    from django.conf import settings as st

    return getattr(st, 'AUTOMATED_LOGGING_DEV', False)


if __name__ == '__main__':
    from automated_logging.helpers import namedtuple2dict

    pprint(namedtuple2dict(default))

settings = Settings()
dev = load_dev()
