"""Tests that perform actions over content unit."""
import unittest

from pulp_smash import utils
from pulp_smash.pulp3.utils import delete_orphans

from galaxy_ng.tests.functional.utils import (
    core_client,
    gen_artifact,
    gen_galaxy_client,
    gen_galaxy_content_attrs,
    monitor_task,
    skip_if,
)
from galaxy_ng.tests.functional.utils import set_up_module as setUpModule  # noqa:F401

from pulpcore.client.pulpcore import ArtifactsApi
from pulpcore.client.galaxy_ng import ApiGalaxyCollectionsApi


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
        delete_orphans()
        cls.content_unit = {}
        cls.galaxy_content_api = ApiGalaxyCollectionsApi(gen_galaxy_client())
        cls.artifact = gen_artifact()

    @classmethod
    def tearDownClass(cls):
        """Clean class-wide variable."""
        delete_orphans()

    def test_01_create_content_unit(self):
        """Create content unit."""
        attrs = gen_galaxy_content_attrs(self.artifact)
        response = self.galaxy_content_api.create(**attrs)
        created_resources = monitor_task(response.task)
        content_unit = self.galaxy_content_api.read(created_resources[0])
        self.content_unit.update(content_unit.to_dict())
        for key, val in attrs.items():
            with self.subTest(key=key):
                self.assertEqual(self.content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_unit(self):
        """Read a content unit by its href."""
        content_unit = self.galaxy_content_api.read(self.content_unit["pulp_href"]).to_dict()
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_units(self):
        """Read a content unit by its relative_path."""
        # FIXME: "relative_path" is an attribute specific to the File plugin. It is only an
        # example. You should replace this with some other field specific to your content type.
        page = self.galaxy_content_api.list(relative_path=self.content_unit["relative_path"])
        self.assertEqual(len(page.results), 1)
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(page.results[0].to_dict()[key], val)

    @skip_if(bool, "content_unit", False)
    def test_03_partially_update(self):
        """Attempt to update a content unit using HTTP PATCH.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = gen_galaxy_content_attrs(self.artifact)
        with self.assertRaises(AttributeError) as exc:
            self.galaxy_content_api.partial_update(self.content_unit["pulp_href"], attrs)
        msg = "object has no attribute 'partial_update'"
        self.assertIn(msg, exc.exception.args[0])

    @skip_if(bool, "content_unit", False)
    def test_03_fully_update(self):
        """Attempt to update a content unit using HTTP PUT.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = gen_galaxy_content_attrs(self.artifact)
        with self.assertRaises(AttributeError) as exc:
            self.galaxy_content_api.update(self.content_unit["pulp_href"], attrs)
        msg = "object has no attribute 'update'"
        self.assertIn(msg, exc.exception.args[0])

    @skip_if(bool, "content_unit", False)
    def test_04_delete(self):
        """Attempt to delete a content unit using HTTP DELETE.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        with self.assertRaises(AttributeError) as exc:
            self.galaxy_content_api.delete(self.content_unit["pulp_href"])
        msg = "object has no attribute 'delete'"
        self.assertIn(msg, exc.exception.args[0])
