#!/usr/bin/env python3

import os
import tempfile
import tarfile
import shutil
import urllib.request
import urllib.error
from distutils import log

from setuptools import find_packages, setup, Command
from setuptools.command.build_py import build_py as _BuildPyCommand
from setuptools.command.sdist import sdist as _SDistCommand

package_name = os.environ.get("GALAXY_NG_ALTERNATE_NAME", "galaxy-ng")
version = "4.6.1"


class PrepareStaticCommand(Command):
    DEV_UI_DOWNLOAD_URL = (
        "https://github.com/ansible/ansible-hub-ui/"
        "releases/download/dev/automation-hub-ui-dist.tar.gz")

    ALTERNATE_UI_DOWNLOAD_URL = os.environ.get("ALTERNATE_UI_DOWNLOAD_URL")

    UI_DOWNLOAD_URL = (
        "https://github.com/ansible/ansible-hub-ui/"
        f"releases/download/{version}/automation-hub-ui-dist.tar.gz"
    )
    TARGET_DIR = "galaxy_ng/app/static/galaxy_ng"

    user_options = [
        (
            'force-download-ui',
            None,
            'Replace any existing static files with the ones downloaded from github.'
        ),
    ]

    def initialize_options(self):
        self.force_download_ui = False

    def finalize_options(self):
        pass

    def run(self):
        if os.path.exists(self.TARGET_DIR):
            if self.force_download_ui:
                log.warn(f"Removing {self.TARGET_DIR} and re downloading the UI.")
                shutil.rmtree(self.TARGET_DIR)
            else:
                log.warn(f"Static directory {self.TARGET_DIR} already exists, skipping. ")
                return

        with tempfile.NamedTemporaryFile() as download_file:
            log.info(f"Downloading UI distribution to temporary file: {download_file.name}")

            if self.ALTERNATE_UI_DOWNLOAD_URL:
                log.info(f"Downloading UI from {self.ALTERNATE_UI_DOWNLOAD_URL}")
                self._download_tarball(self.ALTERNATE_UI_DOWNLOAD_URL, download_file)
            else:
                log.info(f"Attempting to download UI for version {version}")
                try:
                    self._download_tarball(self.UI_DOWNLOAD_URL, download_file)
                except urllib.error.HTTPError:
                    log.warn(f"Failed to retrieve UI for {version}. Downloading latest UI.")
                    self._download_tarball(self.DEV_UI_DOWNLOAD_URL, download_file)

            log.info(f"Extracting UI static files to {self.TARGET_DIR}")
            with tarfile.open(fileobj=download_file) as tfp:
                tfp.extractall(self.TARGET_DIR)

    def _download_tarball(self, url, download_file):
        urllib.request.urlretrieve(url, filename=download_file.name)


class SDistCommand(_SDistCommand):
    def run(self):
        self.run_command('prepare_static')
        return super().run()


class BuildPyCommand(_BuildPyCommand):
    def run(self):
        self.run_command('prepare_static')
        return super().run()


# FIXME: this currently works for CI and dev env, but pip-tools misses dependencies when
# generating requirements.*.txt files. This needs to be fixed before use in the master branch.
def _format_pulp_requirement(plugin, specifier=None, ref=None, gh_namespace="pulp"):
    """
    Formats the pulp plugin requirement.

    The plugin template is VERY picky about the format we use for git refs. This will
    help format git refs in a way that won't break CI when we need to pin to development
    branches of pulp.

    example:
      _format_pulp_requirement("pulpcore", specifier=">=3.18.1,<3.19.0")
      _format_pulp_requirement("pulpcore", ref="6e44fb2fe609f92dc1f502b19c67abd08879148f")
    """
    if specifier:
        return plugin + specifier
    else:
        repo = plugin.replace("-", "_")
        return (
            f"{plugin}@git+https://git@github.com/"
            f"{gh_namespace}/{repo}.git@{ref}#egg={plugin}"
        )


requirements = [
    "galaxy-importer==0.4.5",
    "pulpcore>=3.21.0,<3.22.0",
    "pulp_ansible>=0.15.0,<0.16.0",
    "django-prometheus>=2.0.0",
    "drf-spectacular",
    "pulp-container>=2.14.1,<2.15.0",
    "django-automated-logging==6.1.3",
    "social-auth-core>=3.3.1,<4.0.0",
    "social-auth-app-django>=3.1.0,<4.0.0",
    "dynaconf>=3.1.9",
    "django-auth-ldap==4.0.0",
]


# https://softwareengineering.stackexchange.com/questions/223634/what-is-meant-by-now-you-have-two-problems
def strip_package_name(spec):
    operators = ['=', '>', '<', '~', '!', '^', '@']
    for idc, char in enumerate(spec):
        if char in operators:
            return spec[:idc]
    return spec


# next line can be replaced via sed in ci scripts/post_before_install.sh
unpin_requirements = os.getenv("LOCK_REQUIREMENTS") == "0"
if unpin_requirements:
    """
    To enable the installation of local dependencies e.g: a local fork of
    pulp_ansible checked out to specific branch/version.
    The paths listed on DEV_SOURCE_PATH must be unpinned to avoid pip
    VersionConflict error.
    ref: https://github.com/ansible/galaxy_ng/wiki/Development-Setup
         #steps-to-run-dev-environment-with-specific-upstream-branch
    """
    DEV_SOURCE_PATH = os.getenv(
        "DEV_SOURCE_PATH",
        default="pulpcore:pulp_ansible:pulp_container:galaxy_importer"
    ).split(":")
    DEV_SOURCE_PATH += [path.replace("_", "-") for path in DEV_SOURCE_PATH]
    requirements = [
        strip_package_name(req)
        if req.lower().startswith(tuple(DEV_SOURCE_PATH)) else req
        for req in requirements
    ]
    print("Installing with unpinned DEV_SOURCE_PATH requirements", requirements)

setup(
    name=package_name,
    version=version,
    description="galaxy-ng plugin for the Pulp Project",
    license="GPLv2+",
    author="Red Hat, Inc.",
    author_email="info@ansible.com",
    url="https://github.com/ansible/galaxy_ng/",
    python_requires=">=3.8",
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
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ),
    entry_points={"pulpcore.plugin": ["galaxy_ng = galaxy_ng:default_app_config"]},
    cmdclass={
        "prepare_static": PrepareStaticCommand,
        "build_py": BuildPyCommand,
        "sdist": SDistCommand,
    },
)
