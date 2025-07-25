#!/usr/bin/env python3

import os
import tempfile
import tarfile
import shutil
import urllib.request
import urllib.error
from distutils import log

from setuptools import Command
from setuptools.command.build_py import build_py as _BuildPyCommand
from setuptools.command.sdist import sdist as _SDistCommand


# Import version from the dynamic dependencies module
try:
    from _dynamic_dependencies import version
except ImportError:
    version = "4.11.0dev"  # Fallback version


class PrepareStaticCommand(Command):
    DEV_UI_DOWNLOAD_URL = (
        "https://github.com/ansible/ansible-hub-ui/"
        "releases/download/dev/automation-hub-ui-dist.tar.gz"
    )

    ALTERNATE_UI_DOWNLOAD_URL = os.environ.get("ALTERNATE_UI_DOWNLOAD_URL")

    TARGET_DIR = "galaxy_ng/app/static/galaxy_ng"

    @property
    def UI_DOWNLOAD_URL(self):
        return (
            "https://github.com/ansible/ansible-hub-ui/"
            f"releases/download/{version}/automation-hub-ui-dist.tar.gz"
        )

    user_options = [
        (
            "force-download-ui",
            None,
            "Replace any existing static files with the ones downloaded from github.",
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
        self.run_command("prepare_static")
        return super().run()


class BuildPyCommand(_BuildPyCommand):
    def run(self):
        self.run_command("prepare_static")
        return super().run()
