#!/usr/bin/env python3


from django.test import TestCase
from galaxy_ng.app.utils.galaxy import upstream_role_iterator


class TestGalaxyUtils(TestCase):

    def test_upstream_role_iterator_with_user(self):
        roles = []
        for namespace, role, versions in upstream_role_iterator(github_user="geerlingguy"):
            roles.append(role)
        assert sorted(set([x['github_user'] for x in roles])) == ['geerlingguy']

    def test_upstream_role_iterator_with_user_and_name(self):
        roles = []
        for namespace, role, versions in upstream_role_iterator(github_user="geerlingguy", role_name="docker"):
            roles.append(role)
        assert len(roles) == 1
        assert roles[0]['github_user'] == 'geerlingguy'
        assert roles[0]['name'] == 'docker'

    def test_upstream_role_iterator_with_limit(self):
        count = 0
        for namespace, role, versions in upstream_role_iterator(limit=20):
            count += 1
        assert count == 20
