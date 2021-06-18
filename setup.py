#!/usr/bin/env python3

import os
import tempfile
import tarfile
import urllib.request
from distutils import log

from setuptools import find_packages, setup, Command
from setuptools.command.build_py import build_py as _BuildPyCommand
from setuptools.command.sdist import sdist as _SDistCommand

from galaxy_ng import __version__


class PrepareStaticCommand(Command):
    UI_DOWNLOAD_URL = (
        "https://github.com/ansible/ansible-hub-ui/releases/download/"
        f"{__version__}/automation-hub-ui-dist.tar.gz"
    )
    TARGET_DIR = "galaxy_ng/app/static/galaxy_ng"

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if os.path.exists(self.TARGET_DIR):
            log.warn(f"Static directory {self.TARGET_DIR} already exists, skipping. ")
            return

        with tempfile.NamedTemporaryFile() as download_file:
            log.info(f"Downloading UI distribution to temporary file: {download_file.name}")
            urllib.request.urlretrieve(self.UI_DOWNLOAD_URL, filename=download_file.name)

            log.info(f"Extracting UI static files to {self.TARGET_DIR}")
            with tarfile.open(fileobj=download_file) as tfp:
                tfp.extractall(self.TARGET_DIR)


class SDistCommand(_SDistCommand):
    def run(self):
        self.run_command('prepare_static')
        return super().run()


class BuildPyCommand(_BuildPyCommand):
    def run(self):
        self.run_command('prepare_static')
        return super().run()


requirements = [
    "Django~=2.2.20",
    "galaxy-importer==0.2.15",
    "pulpcore~=3.7.5",
    "pulp-ansible==0.5.8",
    "django-prometheus>=2.0.0",
    "drf-spectacular",
    "ansible~=2.10.0",
    # click 8 requires py38,
    # can be removed once we require >=py38
    "click==7.1.2",
]

package_name = os.environ.get("GALAXY_NG_ALTERNATE_NAME", "galaxy-ng")

setup(
    name=package_name,
    version=__version__,
    description="galaxy-ng plugin for the Pulp Project",
    license="GPLv2+",
    author="Red Hat, Inc.",
    author_email="info@ansible.com",
    url="https://github.com/ansible/galaxy_ng/",
    python_requires=">=3.6",
    setup_requires=["wheel"],
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
        "prepare_static": PrepareStaticCommand,
        "build_py": BuildPyCommand,
        "sdist": SDistCommand,
    },
)
