"""Utility functions for AH tests."""

import shutil
import uuid
from random import randint
import random
import string


def is_docker_installed():
    return shutil.which("docker") is not None


def uuid4():
    """Return a random UUID4 as a string."""
    return str(uuid.uuid4())


def generate_random_string(length=8):
    return str(uuid.uuid4().hex)[:length]


def iterate_all(api_client, url):
    """Iterate through all of the items on every page in a paginated list view."""
    next = url
    key = "data"
    while next is not None:
        r = api_client(next)
        # pulp uses "results"
        if "data" not in r:
            key = "results"
        for x in r[key]:
            yield x
        if "next" in r:
            next = r["next"]
        else:
            next = r["links"]["next"]


def generate_random_artifact_version():
    """Return a string with random integers using format xx.yy.xx."""
    return f"{randint(0, 100)}.{randint(0, 100)}.{randint(1, 100)}"


def gen_string(size=10, chars=string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))
