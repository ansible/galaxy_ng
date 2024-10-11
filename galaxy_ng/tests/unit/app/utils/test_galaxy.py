#!/usr/bin/env python3

import uuid

from django.test import TestCase
from galaxy_ng.app.utils.galaxy import uuid_to_int
from galaxy_ng.app.utils.galaxy import int_to_uuid


class UUIDConversionTestCase(TestCase):

    def test_uuid_to_int_and_back(self):
        """Make sure uuids can become ints and then back to uuids"""
        for x in range(0, 1000):
            test_uuid = str(uuid.uuid4())
            test_int = uuid_to_int(test_uuid)
            reversed_uuid = int_to_uuid(test_int)
            assert test_uuid == reversed_uuid, f"{test_uuid} != {reversed_uuid}"
