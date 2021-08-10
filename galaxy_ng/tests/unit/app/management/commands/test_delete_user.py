from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

User = get_user_model()


class TestDeleteUserCommand(TestCase):
    def setUp(self):
        super().setUp()

    def test_command_output(self):
        with self.assertRaisesMessage(
            CommandError, 'Error: the following arguments are required: --user'
        ):
            call_command('delete-user')

    def test_delete_user(self):
        out = StringIO()
        username = 'system:foo'
        user = User.objects.create(username=username)
        user.save()
        call_command('delete-user', '--user', username, stdout=out)
        self.assertIn("User '{}' deleted".format(username), out.getvalue())

    def test_user_doesnt_exists(self):
        out = StringIO()
        call_command('delete-user', '--user', 'system:bar', stdout=out)
        self.assertIn("User not found", out.getvalue())
