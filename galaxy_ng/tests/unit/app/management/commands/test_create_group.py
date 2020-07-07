from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

User = get_user_model()


class TestCreateGroupCommand(TestCase):
    def setUp(self):
        super().setUp()
        userb = User.objects.create(username='userb')
        userb.save()

    def test_command_output(self):
        with self.assertRaisesMessage(
            CommandError, 'Error: the following arguments are required: groups'
        ):
            call_command('create-group')

    def test_add_group(self):
        out = StringIO()
        call_command('create-group', 'system:foo', stdout=out)
        self.assertIn("Created group 'system:foo'", out.getvalue())

    def test_group_already_exists(self):
        out = StringIO()
        call_command('create-group', 'system:foo', stdout=out)
        call_command('create-group', 'system:foo', stdout=out)
        self.assertIn("Group 'system:foo' already exists", out.getvalue())

    def test_add_group_and_assign(self):
        out = StringIO()
        call_command('create-group', 'system:foo', '--users', 'userb', stdout=out)
        self.assertIn("Assigned group 'system:foo' to user 'userb'", out.getvalue())

    def test_user_not_found(self):
        out = StringIO()
        call_command('create-group', 'system:foo', '--users', 'userz', stdout=out)
        self.assertIn("User 'userz' not found. Skipping", out.getvalue())
