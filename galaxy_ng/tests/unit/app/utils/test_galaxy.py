#!/usr/bin/env python3

import uuid

from django.test import TestCase
from galaxy_ng.app.utils.galaxy import upstream_role_iterator
from galaxy_ng.app.utils.galaxy import uuid_to_int
from galaxy_ng.app.utils.galaxy import int_to_uuid


class TestGalaxyUtils(TestCase):

    def test_upstream_role_iterator_with_user(self):
        roles = []
        for namespace, role, versions in upstream_role_iterator(github_user="jctanner"):
            roles.append(role)
        assert sorted(set([x['github_user'] for x in roles])) == ['jctanner']

    def test_upstream_role_iterator_with_user_and_name(self):
        roles = []
        iterator_kwargs = {
            'github_user': 'geerlingguy',
            'role_name': 'docker'
        }
        for namespace, role, versions in upstream_role_iterator(**iterator_kwargs):
            roles.append(role)
        assert len(roles) == 1
        assert roles[0]['github_user'] == 'geerlingguy'
        assert roles[0]['name'] == 'docker'

    def test_upstream_role_iterator_with_limit(self):
        limit = 10
        count = 0
        for namespace, role, versions in upstream_role_iterator(limit=limit):
            count += 1
        assert count == limit


class UUIDConversionTestCase(TestCase):

    def test_uuid_to_int_and_back(self):
        """Make sure uuids can become ints and then back to uuids"""
        for x in range(0, 1000):
            test_uuid = str(uuid.uuid4())
            test_int = uuid_to_int(test_uuid)
            reversed_uuid = int_to_uuid(test_int)
            assert test_uuid == reversed_uuid, f"{test_uuid} != {reversed_uuid}"
