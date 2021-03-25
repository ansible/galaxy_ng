import tempfile
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase
from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    CollectionRemote,
)

REQUIREMENTS_FILE_STR = (
    "collections:\n"
    "  - name: initial.name\n"
    "    server: https://initial.content.com/v3/collections/\n"
    "    api_key: NotASecret\n"
)


class TestCreateRemoteCommand(TestCase):

    def setUp(self):
        super().setUp()
        CollectionRemote.objects.create(
            name="test-remote",
            url="https://test.remote/v3/collections/"
        )

    def test_command_output(self):
        with self.assertRaisesMessage(
            CommandError, "Error: the following arguments are required: name, url"
        ):
            call_command('create-remote')

    def test_remote_already_exists(self):
        out = StringIO()

        call_command(
            'create-remote',
            'test-remote',
            'https://test.remote/v3/collections/',
            stdout=out
        )

        self.assertIn('Updated existing CollectionRemote test-remote', out.getvalue())
        self.assertIn('Created new Repository test-remote', out.getvalue())
        self.assertIn('Created new Distribution test-remote', out.getvalue())

    def test_remote_created(self):
        out = StringIO()
        call_command('create-remote', 'new-remote', 'https://new.remote/', stdout=out)

        self.assertIn('Created new CollectionRemote new-remote', out.getvalue())
        self.assertIn('Created new Repository new-remote', out.getvalue())
        self.assertIn('Created new Distribution new-remote', out.getvalue())

        self.assertTrue(CollectionRemote.objects.filter(name='new-remote').exists())
        self.assertTrue(AnsibleRepository.objects.filter(name='new-remote').exists())
        self.assertTrue(AnsibleDistribution.objects.filter(base_path='new-remote').exists())

    def test_associate_existing_entities(self):
        out = StringIO()

        existing_remote = CollectionRemote.objects.create(name='existing-remote')
        existing_repository = AnsibleRepository.objects.create(
            name='existing-repo', remote=existing_remote
        )
        AnsibleDistribution.objects.create(
            name='existing-distro', base_path='existing-distro', repository=existing_repository
        )

        call_command(
            'create-remote',
            'new-remote-with-existing-entities',
            'https://new.remote/v3/collections/',
            '--repository', 'existing-repo',
            '--distribution', 'existing-distro',
            stdout=out
        )

        self.assertIn(
            'Created new CollectionRemote new-remote-with-existing-entities',
            out.getvalue()
        )
        self.assertIn('Associated existing Repository existing-repo', out.getvalue())
        self.assertIn('Associated existing Distribution existing-distro', out.getvalue())

        remote = CollectionRemote.objects.get(name='new-remote-with-existing-entities')
        repo = AnsibleRepository.objects.get(name='existing-repo')
        distro = AnsibleDistribution.objects.get(name='existing-distro')

        self.assertEqual(distro.remote.pk, remote.pk)
        self.assertEqual(distro.remote.pk, repo.remote.pk)
        self.assertEqual(distro.repository.pk, repo.pk)
        self.assertEqual(repo.pk, remote.repository_set.first().pk)

    def test_invalid_url(self):
        with self.assertRaisesMessage(
            CommandError, "url should end with '/'"
        ):
            call_command('create-remote', 'invalid-remote', 'https://invalid.url/foo')

    def test_cannot_create_community_wo_requirements_file(self):
        with self.assertRaisesMessage(
            CommandError,
            'Syncing content from community domains without specifying a '
            'requirements file is not allowed.'
        ):
            call_command('create-remote', 'community', 'https://galaxy.ansible.com/v3/collections/')

    def test_create_community_remote_with_requirements_file_str(self):
        out = StringIO()
        call_command(
            'create-remote',
            'My New Remote',
            'https://galaxy.ansible.com/v3/collections/',
            '-r', REQUIREMENTS_FILE_STR,
            stdout=out
        )

        self.assertIn('Created new CollectionRemote my-new-remote', out.getvalue())
        self.assertIn('Created new Repository my-new-remote', out.getvalue())
        self.assertIn('Created new Distribution my-new-remote', out.getvalue())

        self.assertEqual(
            CollectionRemote.objects.get(name='my-new-remote').requirements_file,
            REQUIREMENTS_FILE_STR
        )

    def test_invalid_requirements_file(self):
        with self.assertRaisesMessage(
            CommandError,
            "Error parsing requirements_file"
        ):
            call_command('create-remote', 'foo', 'https://bar.com/', '-r', 'invalid_file_str')

    def test_load_requirements_file_from_path(self):
        out = StringIO()

        with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml') as requirements_file:
            requirements_file.write(REQUIREMENTS_FILE_STR)
            requirements_file.seek(0)

            call_command(
                'create-remote',
                'community-from-file',
                'https://galaxy.ansible.com/v3/collections/',
                '-r', requirements_file.name,
                stdout=out
            )

            self.assertIn('Created new CollectionRemote community', out.getvalue())
            self.assertIn('Created new Repository community', out.getvalue())
            self.assertIn('Created new Distribution community', out.getvalue())

            self.assertIn('requirements_file loaded and parsed', out.getvalue())
