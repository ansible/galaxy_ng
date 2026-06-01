from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class TestListAllUsersCommand(TestCase):
    def test_no_users(self):
        """Test output when no users exist"""
        out = StringIO()
        call_command('list-all-users', stdout=out)
        self.assertIn("No users found", out.getvalue())

    def test_list_single_user(self):
        """Test output with one user"""
        User = get_user_model()
        User.objects.create(username='testuser1')

        out = StringIO()
        call_command('list-all-users', stdout=out)
        output = out.getvalue()

        self.assertIn("Found 1 user(s):", output)
        self.assertIn("testuser1", output)

    def test_list_multiple_users(self):
        """Test output with multiple users"""
        User = get_user_model()
        User.objects.create(username='alice')
        User.objects.create(username='bob')
        User.objects.create(username='charlie')

        out = StringIO()
        call_command('list-all-users', stdout=out)
        output = out.getvalue()

        self.assertIn("Found 3 user(s):", output)
        self.assertIn("alice", output)
        self.assertIn("bob", output)
        self.assertIn("charlie", output)
