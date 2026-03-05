from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

User = get_user_model()


class TestDeleteUserCommand(TestCase):
    def setUp(self):
        super().setUp()
        # Create simple test users
        User.objects.create_user(username='testuser1', email='test1@example.com')
        User.objects.create_user(username='testuser2', email='test2@example.com')
        User.objects.create_user(username='testuser3', email='test3@example.com')

    def test_command_output(self):
        with self.assertRaisesMessage(
            CommandError, 'Error: the following arguments are required: --user'
        ):
            call_command('delete-user')

    def test_list_users(self):
        out = StringIO()
        call_command('list-all-users', stdout=out)
        output = out.getvalue()

        self.assertIn('testuser1', output)
        self.assertIn('testuser2', output)
        self.assertIn('testuser3', output)
        self.assertIn('test1@example.com', output)
        self.assertIn('test2@example.com', output)
        self.assertIn('test3@example.com', output)

    def test_list_users_no_data(self):
        # Delete all users
        User.objects.all().delete()
        
        out = StringIO()
        call_command('list-all-users', stdout=out)
        
        self.assertIn('No users found', out.getvalue())
