#!/usr/bin/env python3

import os
import re
import tempfile
import tarfile
import urllib.request
from distutils import log

from setuptools import find_packages, setup, Command
from setuptools.command.build_py import build_py as _BuildPyCommand
from setuptools.command.sdist import sdist as _SDistCommand


class PrepareStaticCommand(Command):
    if os.environ.get("ALTERNATE_UI_DOWNLOAD_URL"):
        UI_DOWNLOAD_URL = os.environ.get("ALTERNATE_UI_DOWNLOAD_URL")
    else:
        UI_DOWNLOAD_URL = (
            "https://github.com/ansible/ansible-hub-ui/releases"
            "/latest/download/automation-hub-ui-dist.tar.gz"
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
    "Django~=2.2.18",
    "galaxy-importer==0.3.0",
    "pulpcore<3.12,>=3.11",
    "pulp-ansible==0.7.1",
    "django-prometheus>=2.0.0",
    "drf-spectacular",
    "pulp-container>=2.5.1",
]


is_on_dev_environment = (
    "COMPOSE_PROFILE" in os.environ and "DEV_SOURCE_PATH" in os.environ
    and os.environ.get("LOCK_REQUIREMENTS") == "0"
)
if is_on_dev_environment:
    """
    To enable the installation of local dependencies e.g: a local fork of
    pulp_ansible checked out to specific branch/version.
    The paths listed on DEV_SOURCE_PATH must be unpinned to avoid pip
    VersionConflict error.
    ref: https://github.com/ansible/galaxy_ng/wiki/Development-Setup
         #steps-to-run-dev-environment-with-specific-upstream-branch
    """
    DEV_SOURCE_PATH = os.environ.get("DEV_SOURCE_PATH", "").split(":")
    DEV_SOURCE_PATH += [path.replace("_", "-") for path in DEV_SOURCE_PATH]
    requirements = [
        re.sub(r"""(=|^|~|<|>|!)([\S]+)""", "", req)
        if req.lower().startswith(tuple(DEV_SOURCE_PATH)) else req
        for req in requirements
    ]
    print("Installing with unpinned DEV_SOURCE_PATH requirements", requirements)

package_name = os.environ.get("GALAXY_NG_ALTERNATE_NAME", "galaxy-ng")
version = "4.3.0a2"

setup(
    name=package_name,
    version=version,
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
