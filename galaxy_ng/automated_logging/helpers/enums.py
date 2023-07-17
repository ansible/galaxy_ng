""" Various enums used in DAL """

from enum import Enum


class Operation(int, Enum):
    """
    Simple Enum that will be used across the code to
    indicate the current operation that happened.

    Due to the fact that enum support for django was
    only added in 3.0 we have DjangoOperations to convert
    it to the old django format.
    """

    CREATE = 1
    MODIFY = 0
    DELETE = -1


DjangoOperations = [(e.value, o.lower()) for o, e in Operation.__members__.items()]
VerbOperationMap = {
    'create': Operation.CREATE,
    'modify': Operation.MODIFY,
    'delete': Operation.DELETE,
    'add': Operation.CREATE,
    'remove': Operation.DELETE,
}
VerbM2MOperationMap = {
    'add': Operation.CREATE,
    'modify': Operation.MODIFY,
    'remove': Operation.DELETE,
}
PastOperationMap = {
    'created': Operation.CREATE,
    'modified': Operation.MODIFY,
    'deleted': Operation.DELETE,
}
PastM2MOperationMap = {
    'added': Operation.CREATE,
    'modified': Operation.MODIFY,
    'removed': Operation.DELETE,
}
ShortOperationMap = {
    '+': Operation.CREATE,
    '~': Operation.MODIFY,
    '-': Operation.DELETE,
}
TranslationOperationMap = {**VerbOperationMap, **PastOperationMap, **ShortOperationMap}
