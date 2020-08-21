from io import StringIO
from django.core.management import call_command, CommandError
from django.test import TestCase
from galaxy_ng.app.models.auth import Group


class TestAssignPermissionCommand(TestCase):
    def setUp(self):
        super().setUp()
        group = Group.objects.create(name='administrator')
        group.save()

    def test_command_output(self):
        with self.assertRaisesMessage(
            CommandError,
            'Error: the following arguments are required: group, permissions'
        ):
            call_command('assign-permission')

    def test_add_permission(self):
        out = StringIO()
        call_command(
            'assign-permission', 'administrator', 'galaxy.add_namespace',
            stdout=out)
        self.assertIn(
            "Assigned requested permission to group 'administrator'",
            out.getvalue())
        admin_group = Group.objects.get(name='administrator')
        self.assertIn(
            'add_namespace',
            [perm.codename for perm in admin_group.permissions.all()]
        )

    def test_add_multiple_permissions(self):
        out = StringIO()
        call_command('assign-permission', 'administrator',
                     'galaxy.add_namespace', 'galaxy.change_namespace', stdout=out)
        self.assertIn("Assigned requested permission to group 'administrator'", out.getvalue())
        admin_group = Group.objects.get(name='administrator')
        self.assertIn(
            'add_namespace',
            [perm.codename for perm in admin_group.permissions.all()]
        )

    def test_group_not_found(self):
        with self.assertRaisesMessage(
            CommandError,
            'Group system:foo does not exist. Please provide a valid group '
            'name'
        ):
            call_command('assign-permission', 'system:foo',
                         'galaxy.add_namespace')

    def test_permission_not_found(self):
        out = StringIO()
        with self.assertRaisesMessage(
            CommandError,
                "Permission galaxy.foo not found. Please provide a valid "
                "permission in the form 'app_label.codename'"
        ):
            call_command('assign-permission', 'administrator', 'galaxy.foo',
                         stdout=out)

    def test_permission_format(self):
        out = StringIO()
        with self.assertRaisesMessage(
            CommandError,
                "Invalid permission format for foo. Expecting "
                "'app_label.codename'"
        ):
            call_command('assign-permission', 'administrator', 'foo',
                         stdout=out)
