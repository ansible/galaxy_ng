#!/usr/bin/env python3

import os
import tempfile
import tarfile
import urllib.request
from distutils import log

from setuptools.command.build_py import build_py as _BuildPyCommand
from setuptools import find_packages, setup

from galaxy_ng import __version__


class BuildPyCommand(_BuildPyCommand):
    """Custom build command."""

    UI_DOWNLOAD_URL = (
        'https://github.com/ansible/ansible-hub-ui/releases'
        '/latest/download/automation-hub-ui-dist.tar.gz'
    )

    def run(self):
        target_dir = os.path.join(self.build_lib, 'galaxy_ng/app/static/galaxy_ng')

        with tempfile.NamedTemporaryFile() as download_file:
            log.info(f'Downloading UI distribution {download_file.name}')
            urllib.request.urlretrieve(self.UI_DOWNLOAD_URL, filename=download_file.name)

            log.info(f'Extracting UI static files')
            with tarfile.open(fileobj=download_file) as tfp:
                tfp.extractall(target_dir)

        super().run()


# NOTE(cutwater): Because bindings are statically generated, requirements list
#   from pulp-galaxy/setup.py has to be copied here and manually maintained.
galaxy_pulp_requirements = [
    "urllib3 >= 1.15",
    "six >= 1.10",
    "certifi",
    "python-dateutil"
]

requirements = galaxy_pulp_requirements + [
    "Django~=2.2.3",
    "pulpcore>=3.0,<3.4",
    "pulp-ansible>=0.2.0b11",
    "django-prometheus>=2.0.0",
    "django-storages[boto3]",
]

setup(
    name="galaxy-ng",
    version=__version__,
    description="galaxy-ng plugin for the Pulp Project",
    license="GPLv2+",
    author="AUTHOR",
    author_email="author@email.here",
    url="http://example.com/",
    python_requires=">=3.6",
    setup_requires=['wheel'],
    install_requires=requirements,
    include_package_data=True,
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=(
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: POSIX :: Linux",
        "Framework :: Django",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ),
    entry_points={"pulpcore.plugin": ["galaxy_ng = galaxy_ng:default_app_config"]},
    cmdclass={
        'build_py': BuildPyCommand,
    },
)
