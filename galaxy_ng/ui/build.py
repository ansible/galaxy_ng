import os
import tempfile
import tarfile
import shutil
import urllib.request
import urllib.error
from distutils import log

from setuptools.command.build_py import build_py as _BuildPyCommand
from setuptools.command.sdist import sdist as _SDistCommand

version = "4.11.0dev"

DEV_UI_DOWNLOAD_URL = (
    "https://github.com/ansible/ansible-hub-ui/"
    "releases/download/dev/automation-hub-ui-dist.tar.gz"
)

ALTERNATE_UI_DOWNLOAD_URL = os.environ.get("ALTERNATE_UI_DOWNLOAD_URL")

UI_DOWNLOAD_URL = (
    "https://github.com/ansible/ansible-hub-ui/"
    f"releases/download/{version}/automation-hub-ui-dist.tar.gz"
)
TARGET_DIR = "galaxy_ng/app/static/galaxy_ng"

FORCE_DOWNLOAD_UI = os.environ.get("FORCE_DOWNLOAD_UI", False)


def prepare_static():
    if os.path.exists(TARGET_DIR):
        if FORCE_DOWNLOAD_UI:
            log.warn(f"Removing {TARGET_DIR} and re downloading the UI.")
            shutil.rmtree(TARGET_DIR)
        else:
            log.warn(f"Static directory {TARGET_DIR} already exists, skipping. ")
            return

    with tempfile.NamedTemporaryFile() as download_file:
        log.info(f"Downloading UI distribution to temporary file: {download_file.name}")

        if ALTERNATE_UI_DOWNLOAD_URL:
            log.info(f"Downloading UI from {ALTERNATE_UI_DOWNLOAD_URL}")
            _download_tarball(ALTERNATE_UI_DOWNLOAD_URL, download_file)
        else:
            log.info(f"Attempting to download UI for version {version}")
            try:
                _download_tarball(UI_DOWNLOAD_URL, download_file)
            except urllib.error.HTTPError:
                log.warn(f"Failed to retrieve UI for {version}. Downloading latest UI.")
                _download_tarball(DEV_UI_DOWNLOAD_URL, download_file)

        log.info(f"Extracting UI static files to {TARGET_DIR}")
        with tarfile.open(fileobj=download_file) as tfp:
            tfp.extractall(TARGET_DIR)


def _download_tarball(url, download_file):
    urllib.request.urlretrieve(url, filename=download_file.name)


class SDistCommand(_SDistCommand):
    def run(self):
        prepare_static()
        return super().run()


class BuildPyCommand(_BuildPyCommand):
    def run(self):
        prepare_static()
        return super().run()
