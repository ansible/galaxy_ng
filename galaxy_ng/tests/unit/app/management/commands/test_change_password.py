from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase
from unittest import mock

User = get_user_model()


class TestChangePasswordCommand(TestCase):
    def setUp(self):
        foo = User.objects.create(username="russell")
        foo.set_password("russel@llen$1")
        foo.save()
        super().setUp()

    @mock.patch(
        "django.contrib.auth.management.commands.changepassword.getpass.getpass"
    )
    def test_password_minimum_length(self, mock_getpass=None):
        def input_response(*args, **kwargs):
            return "12345"  # it requires 9 length

        mock_getpass.side_effect = input_response
        out = StringIO()
        err = StringIO()
        with self.assertRaisesMessage(
            CommandError,
            "Aborting password change for user 'russell' after 3 attempts",
        ):
            call_command("changepassword", "russell", stdout=out, stderr=err)

        self.assertIn(
            "This password is too short. It must contain at least 9 characters.",
            err.getvalue(),
        )
