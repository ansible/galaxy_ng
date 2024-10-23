"""Utility functions for AH tests."""

import shutil
import uuid
from random import SystemRandom
import string


random = SystemRandom()


def is_docker_installed():
    return shutil.which("docker") is not None


def uuid4():
    """Return a random UUID4 as a string."""
    return str(uuid.uuid4())


# REFACTORING: Deprecate and replace with random_name() function.
def generate_random_string(length=8):
    return str(uuid.uuid4().hex)[:length]


def random_name(prefix: str, *, length: int = 8, sep: str = '-'):
    """Generate random name."""
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return f"{prefix}{sep}{suffix}"


def iterate_all(api_client, url, gc=None):
    """Iterate through all of the items on every page in a paginated list view."""
    next_ = url
    key = "data"
    while next_ is not None:
        if gc:
            r = gc.get(next_)
        else:
            r = api_client(next_)
        # pulp uses "results"
        if "data" not in r:
            key = "results"
        yield from r[key]
        if "next" in r:
            next_ = r["next"]
        else:
            next_ = r["links"]["next"]


def generate_random_artifact_version():
    """Return a string with random integers using format xx.yy.xx."""
    return f"{random.randint(0, 100)}.{random.randint(0, 100)}.{random.randint(1, 100)}"


def gen_string(size=10, chars=string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))


def iterate_all_gk(gc_admin, url):
    """Iterate through all of the items on every page in a paginated list view."""
    next_ = url
    key = "data"
    while next_ is not None:
        r = gc_admin.get(next_)
        # pulp uses "results"
        if "data" not in r:
            key = "results"
        yield from r[key]
        if "next" in r:
            next_ = r["next"]
        else:
            next_ = r["links"]["next"]
