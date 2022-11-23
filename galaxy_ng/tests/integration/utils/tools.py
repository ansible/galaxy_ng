"""Utility functions for AH tests."""

import shutil
import uuid
from random import randint


def is_docker_installed():
    return shutil.which("docker") is not None


def uuid4():
    """Return a random UUID4 as a string."""
    return str(uuid.uuid4())


def generate_random_artifact_version():
    """Return a string with random integers using format xx.yy.xx."""
    return f"{randint(0, 100)}.{randint(0, 100)}.{randint(1, 100)}"