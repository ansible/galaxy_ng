"""Utility functions for AH tests."""

import json
import logging
import os
import shutil
import subprocess
import tempfile


logger = logging.getLogger(__name__)


class CollectionInspector:

    """ Easy shim to look at tarballs or installed collections """

    def __init__(self, tarball=None, directory=None):
        self.tarball = tarball
        self.directory = directory
        self.manifest = None
        self._extract_path = None
        self._enumerate()

    def _enumerate(self):
        if self.tarball:
            self._extract_path = tempfile.mkdtemp(prefix='collection-extract-')
            cmd = f'cd {self._extract_path}; tar xzvf {self.tarball}'
            subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            self._extract_path = self.directory

        with open(os.path.join(self._extract_path, 'MANIFEST.json'), 'r') as f:
            self.manifest = json.loads(f.read())

        if self.tarball:
            shutil.rmtree(self._extract_path)

    @property
    def namespace(self):
        if self.manifest is None:
            return None
        return self.manifest['collection_info']['namespace']

    @property
    def name(self):
        if self.manifest is None:
            return None
        return self.manifest['collection_info']['name']

    @property
    def tags(self):
        if self.manifest is None:
            return None
        return self.manifest['collection_info']['tags']

    @property
    def version(self):
        if self.manifest is None:
            return None
        return self.manifest['collection_info']['version']
