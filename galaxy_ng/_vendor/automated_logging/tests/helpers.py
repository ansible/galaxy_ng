""" test specific helpers """

import string
from random import choice


def random_string(length=10):
    """ generate a random string with the length specified """
    return ''.join(choice(string.ascii_letters) for _ in range(length))
