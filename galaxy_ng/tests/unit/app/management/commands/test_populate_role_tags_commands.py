from django.core.management import call_command
from django.test import TestCase

from galaxy_ng.app.api.v1.models import LegacyNamespace, LegacyRole, LegacyRoleTag


class TestPopulateRoleTagsCommand(TestCase):

    def _load_role(self, namespace, role, tags):
        full_metadata = dict(tags=tags)
        ln = LegacyNamespace.objects.get_or_create(name=namespace)
        LegacyRole.objects.get_or_create(name=role, namespace=ln[0], full_metadata=full_metadata)

    def setUp(self):
        super().setUp()
        self._load_role("foo", "bar1", ["database", "network", "postgres"])
        self._load_role("foo", "bar2", ["database", "network"])

    def test_populate_role_tags_command(self):
        call_command('populate-role-tags')

        role_tags = LegacyRoleTag.objects.all()
        tag_names = list(role_tags.values_list("name", flat=True))

        self.assertEqual(3, role_tags.count())
        self.assertEqual(tag_names, ["database", "network", "postgres"])

    def test_populate_twice_and_expect_same_results(self):
        call_command('populate-role-tags')
        role_tags_1 = LegacyRoleTag.objects.all()
        self.assertEqual(3, role_tags_1.count())

        call_command('populate-role-tags')
        role_tags_2 = LegacyRoleTag.objects.all()
        self.assertEqual(role_tags_1.count(), role_tags_2.count())

    def test_populate_detected_changes(self):
        call_command('populate-role-tags')
        role_tags = LegacyRoleTag.objects.all()
        self.assertEqual(3, role_tags.count())

        self._load_role("foo", "bar3", ["database", "network", "mysql"])
        call_command('populate-role-tags')
        role_tags = LegacyRoleTag.objects.all()
        self.assertEqual(4, role_tags.count())
