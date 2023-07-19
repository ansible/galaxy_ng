import re
import typing
from collections import namedtuple
from datetime import timedelta
from typing import NamedTuple

from marshmallow import Schema, EXCLUDE, post_load
from marshmallow.fields import List, String, Nested, TimeDelta

from automated_logging.helpers.exceptions import NoMatchFound, CouldNotConvertError

Search = NamedTuple('Search', (('type', str), ('value', str)))
Search._serialize = lambda self: f'{self.type}:{self.value}'


class Set(List):
    """
    This is like a list, just compiles down to a set when serializing.
    """

    def _serialize(
        self, value, attr, obj, **kwargs
    ) -> typing.Optional[typing.Set[typing.Any]]:
        return set(super(Set, self)._serialize(value, attr, obj, **kwargs))

    def _deserialize(self, value, attr, data, **kwargs) -> typing.Set[typing.Any]:
        return set(super(Set, self)._deserialize(value, attr, data, **kwargs))


class LowerCaseString(String):
    """
    String that is always going to be serialized to a lowercase string,
    using `str.lower()`
    """

    def _deserialize(self, value, attr, data, **kwargs) -> str:
        output = super()._deserialize(value, attr, data, **kwargs)

        return output.lower()


class Duration(TimeDelta):
    """ TimeDelta derivative, with more input methods """

    def _convert(
        self, target: typing.Union[int, str, timedelta, None]
    ) -> typing.Optional[timedelta]:
        if target is None:
            return None

        if isinstance(target, timedelta):
            return target

        if isinstance(target, int) or isinstance(target, float):
            return timedelta(seconds=target)

        if isinstance(target, str):
            REGEX = (
                r'^P(?!$)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+S)?)?$'
            )
            match = re.match(REGEX, target, re.IGNORECASE)
            if not match:
                raise self.make_error('invalid') from NoMatchFound

            components = list(match.groups())
            # remove leading T capture - isn't used, by removing the 5th capture group
            components.pop(4)

            adjusted = {'days': 0, 'seconds': 0}
            conversion = [
                ['days', 365],  # year
                ['days', 30],  # month
                ['days', 7],  # week
                ['days', 1],  # day
                ['seconds', 3600],  # hour
                ['seconds', 60],  # minute
                ['seconds', 1],  # second
            ]

            for pointer in range(len(components)):
                if not components[pointer]:
                    continue
                rate = conversion[pointer]
                native = int(re.findall(r'(\d+)', components[pointer])[0])

                adjusted[rate[0]] += native * rate[1]

            return timedelta(**adjusted)

        raise self.make_error('invalid') from CouldNotConvertError

    def _deserialize(self, value, attr, data, **kwargs) -> typing.Optional[timedelta]:
        try:
            output = self._convert(value)
        except OverflowError as error:
            raise self.make_error('invalid') from error

        return output


class SearchString(String):
    """
    Used for:
    - ModelString
    - FieldString
    - ApplicationString
    - FileString

    SearchStrings are used for models, fields and applications.
    They can be either a glob (prefixed with either glob or gl),
    regex (prefixed with either regex or re)
    or plain (prefixed with plain or pl).

    All SearchStrings ignore the case of the raw string.

    format: <prefix>:<value>
    examples:
        - gl:app*       (glob matching)
        - glob:app*     (glob matching)
        - pl:app        (exact matching)
        - plain:app     (exact matching)
        - re:^app.*$    (regex matching)
        - regex:^app.*$ (regex matching)
        - :app*         (glob matching)
        - app           (glob matching)
    """

    def _deserialize(self, value, attr, data, **kwargs) -> Search:
        if isinstance(value, dict) and 'type' in value and 'value' in value:
            value = f'{value["type"]}:{value["value"]}'

        output = super()._deserialize(value, attr, data, **kwargs)

        match = re.match(r'^(\w*):(.*)$', output, re.IGNORECASE)
        if match:
            module = match.groups()[0].lower()
            match = match.groups()[1]

            if module.startswith('gl'):
                return Search('glob', match.lower())
            elif module.startswith('pl'):
                return Search('plain', match.lower())
            elif module.startswith('re'):
                # regex shouldn't be lowercase
                # we just ignore the case =
                return Search('regex', match)

            raise self.make_error('invalid') from NotImplementedError

        return Search('glob', output)


class MissingNested(Nested):
    """
    Modified marshmallow Nested, that is defaulting missing to loading an empty
    schema, to populate it with data.
    """

    def __init__(self, *args, **kwargs):
        if 'missing' not in kwargs:
            kwargs['missing'] = lambda: args[0]().load({})

        super().__init__(*args, **kwargs)


class BaseSchema(Schema):
    """
    Modified marshmallow Schema, that is defaulting the unknown keyword to EXCLUDE,
    not RAISE (marshmallow default) and when loading converts the dict into a namedtuple.
    """

    def __init__(self, *args, **kwargs):
        if 'unknown' not in kwargs:
            kwargs['unknown'] = EXCLUDE

        super().__init__(*args, **kwargs)

    @staticmethod
    def namedtuple_or(left: NamedTuple, right: NamedTuple):
        """
        __or__ implementation for the namedtuple
        """
        values = {}

        if not isinstance(left, tuple) or not isinstance(right, tuple):
            raise NotImplementedError

        for name in left._fields:
            field = getattr(left, name)
            values[name] = field

            if not hasattr(right, name):
                continue

            if isinstance(field, tuple) or isinstance(field, set):
                values[name] = field | getattr(right, name)

        return left._replace(**values)

    @staticmethod
    def namedtuple_factory(name, keys):
        """
        create the namedtuple from the name and keys to attach functions that are needed.

        Attaches:
            binary **or** operation to support globals propagation
        """
        Object = namedtuple(name, keys)
        Object.__or__ = BaseSchema.namedtuple_or
        return Object

    @post_load
    def make_namedtuple(self, data: typing.Dict, **kwargs):
        """
        converts the loaded data dict into a namedtuple

        :param data: loaded data
        :param kwargs: marshmallow kwargs
        :return: namedtuple
        """
        name = self.__class__.__name__.replace('Schema', '')

        Object = BaseSchema.namedtuple_factory(name, data.keys())
        return Object(**data)
