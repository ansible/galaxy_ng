from io import StringIO
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class TestListAllUsersCommand(TestCase):
    def setUp(self):
        super().setUp()

    def test_no_users(self):
        out = StringIO()
        call_command('list_all_users', stdout=out)
        self.assertIn("No users found.", out.getvalue())

    def test_list_users(self):
        User.objects.create_user(username='user1', password='testpass')
        User.objects.create_user(username='user2', password='testpass')
        out = StringIO()
        call_command('list_all_users', stdout=out)
        output = out.getvalue()
        self.assertIn("user1", output)
        self.assertIn("user2", output)
