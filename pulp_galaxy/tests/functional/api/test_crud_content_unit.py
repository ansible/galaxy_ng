# coding=utf-8
"""Tests that perform actions over content unit."""
import unittest

from requests.exceptions import HTTPError

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import ARTIFACTS_PATH
from pulp_smash.pulp3.utils import delete_orphans

from pulp_galaxy.tests.functional.constants import GALAXY_CONTENT_PATH, GALAXY_URL
from pulp_galaxy.tests.functional.utils import gen_galaxy_content_attrs, skip_if
from pulp_galaxy.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


# Read the instructions provided below for the steps needed to enable this test (see: FIXME's).
@unittest.skip("FIXME: plugin writer action required")
class ContentUnitTestCase(unittest.TestCase):
    """CRUD content unit.

    This test targets the following issues:

    * `Pulp #2872 <https://pulp.plan.io/issues/2872>`_
    * `Pulp #3445 <https://pulp.plan.io/issues/3445>`_
    * `Pulp Smash #870 <https://github.com/pulp/pulp-smash/issues/870>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variable."""
        cls.cfg = config.get_config()
        delete_orphans(cls.cfg)
        cls.content_unit = {}
        cls.client = api.Client(cls.cfg, api.json_handler)
        files = {"file": utils.http_get(GALAXY_URL)}
        cls.artifact = cls.client.post(ARTIFACTS_PATH, files=files)

    @classmethod
    def tearDownClass(cls):
        """Clean class-wide variable."""
        delete_orphans(cls.cfg)

    def test_01_create_content_unit(self):
        """Create content unit."""
        attrs = gen_galaxy_content_attrs(self.artifact)
        self.content_unit.update(self.client.post(GALAXY_CONTENT_PATH, attrs))
        for key, val in attrs.items():
            with self.subTest(key=key):
                self.assertEqual(self.content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_unit(self):
        """Read a content unit by its href."""
        content_unit = self.client.get(self.content_unit["pulp_href"])
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_units(self):
        """Read a content unit by its relative_path."""
        # FIXME: "relative_path" is an attribute specific to the File plugin. It is only an
        # example. You should replace this with some other field specific to your content type.
        page = self.client.get(
            GALAXY_CONTENT_PATH, params={"relative_path": self.content_unit["relative_path"]}
        )
        self.assertEqual(len(page["results"]), 1)
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(page["results"][0][key], val)

    @skip_if(bool, "content_unit", False)
    def test_03_partially_update(self):
        """Attempt to update a content unit using HTTP PATCH.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = gen_galaxy_content_attrs(self.artifact)
        with self.assertRaises(HTTPError) as exc:
            self.client.patch(self.content_unit["pulp_href"], attrs)
        self.assertEqual(exc.exception.response.status_code, 405)

    @skip_if(bool, "content_unit", False)
    def test_03_fully_update(self):
        """Attempt to update a content unit using HTTP PUT.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = gen_galaxy_content_attrs(self.artifact)
        with self.assertRaises(HTTPError) as exc:
            self.client.put(self.content_unit["pulp_href"], attrs)
        self.assertEqual(exc.exception.response.status_code, 405)

    @skip_if(bool, "content_unit", False)
    def test_04_delete(self):
        """Attempt to delete a content unit using HTTP DELETE.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        with self.assertRaises(HTTPError) as exc:
            self.client.delete(self.content_unit["pulp_href"])
        self.assertEqual(exc.exception.response.status_code, 405)
