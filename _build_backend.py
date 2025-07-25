#!/usr/bin/env python3

"""Custom build backend for galaxy_ng with dynamic dependencies support."""

import os
from contextlib import contextmanager
from setuptools import build_meta as _orig
from setuptools.build_meta import *  # noqa: F403, F401


@contextmanager
def _temporary_setup_py():
    """Context manager to create and cleanup temporary setup.py with dynamic metadata."""
    from _dynamic_dependencies import get_dependencies, version, get_package_name

    setup_py_content = f'''#!/usr/bin/env python3
from setuptools import setup

setup(
    version="{version}",
    name="{get_package_name()}",
    install_requires={repr(get_dependencies())},
)
'''

    # Write temporary setup.py
    with open('setup.py', 'w') as f:
        f.write(setup_py_content)

    try:
        yield
    finally:
        # Cleanup: remove temporary setup.py if it exists
        if os.path.exists('setup.py'):
            os.remove('setup.py')


def get_requires_for_build_wheel(config_settings=None):
    """Get requirements for building wheel."""
    return _orig.get_requires_for_build_wheel(config_settings)


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    """Prepare metadata for building wheel with dynamic dependencies."""
    with _temporary_setup_py():
        return _orig.prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """Build wheel with dynamic dependencies."""
    with _temporary_setup_py():
        return _orig.build_wheel(wheel_directory, config_settings, metadata_directory)


def get_requires_for_build_sdist(config_settings=None):
    """Get requirements for building sdist."""
    return _orig.get_requires_for_build_sdist(config_settings)


def build_sdist(sdist_directory, config_settings=None):
    """Build sdist with dynamic dependencies."""
    with _temporary_setup_py():
        return _orig.build_sdist(sdist_directory, config_settings)


def get_requires_for_build_editable(config_settings=None):
    """Get requirements for building editable install."""
    return _orig.get_requires_for_build_editable(config_settings)


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    """Prepare metadata for building editable install with dynamic dependencies."""
    with _temporary_setup_py():
        return _orig.prepare_metadata_for_build_editable(metadata_directory, config_settings)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    """Build editable install with dynamic dependencies."""
    with _temporary_setup_py():
        return _orig.build_editable(wheel_directory, config_settings, metadata_directory)
