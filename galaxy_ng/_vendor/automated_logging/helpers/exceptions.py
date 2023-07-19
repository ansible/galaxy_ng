""" custom exceptions """


class NoMatchFound(Exception):
    """ error that indicates that no match has been found for a regex """

    pass


class CouldNotConvertError(Exception):
    """ error that is thrown when no conversion could be done """

    pass
