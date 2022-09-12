"""Utility functions for AH tests."""

import shutil
import uuid


def is_docker_installed():
    return shutil.which("docker") is not None


def uuid4():
    """Return a random UUID4 as a string."""
    return str(uuid.uuid4())
