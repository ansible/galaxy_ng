from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

User = get_user_model()


class TestCreateUserCommand(TestCase):
    def setUp(self):
        super().setUp()

    def test_command_output(self):
        with self.assertRaisesMessage(
            CommandError, 'Error: the following arguments are required: --user'
        ):
            call_command('create-user')

    def test_add_user(self):
        out = StringIO()
        call_command('create-user', '--user', 'system:foo', stdout=out)
        self.assertIn("Created user 'system:foo'", out.getvalue())

    def test_user_already_exists(self):
        out = StringIO()
        call_command('create-user', '--user', 'system:foo', stdout=out)
        call_command('create-user', '--user', 'system:foo', stdout=out)
        self.assertIn("User 'system:foo' already exists", out.getvalue())
