from django.core.management import CommandError, call_command
from django.test import TestCase
from pulp_ansible.app.models import AnsibleRepository


CMD = "set-retain-repo-versions"


class TestSetRetainRepoVersionsCommand(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.original_data = list(
            AnsibleRepository.objects.all().values("name", "retain_repo_versions")
        )

    @classmethod
    def tearDownClass(cls):
        for data in cls.original_data:
            repo = AnsibleRepository.objects.get(name=data["name"])
            repo.retain_repo_versions = data["retain_repo_versions"]
            repo.save()

    def test_command_output(self):
        with self.assertRaisesMessage(
            CommandError, "Error: the following arguments are required: --value, --repository"
        ):
            call_command(CMD, "--yes")

    def test_set_all_to_2(self):
        """All the repos gets retain_repo_versions set to 2"""
        call_command(CMD, "--yes", "--value", "2", "--repository", "*")
        for repo in AnsibleRepository.objects.all():
            self.assertEqual(repo.retain_repo_versions, 2)

    def test_set_only_published_to_1000(self):
        """Only published is set to 1000"""
        repo = AnsibleRepository.objects.get(name="published")
        repo.retain_repo_versions = 1
        repo.save()
        call_command(CMD, "--yes", "--value", "1000", "--repository", "published")
        repo = AnsibleRepository.objects.get(name="published")

        self.assertEqual(repo.retain_repo_versions, 1000)

        for repo in AnsibleRepository.objects.exclude(name="published"):
            self.assertNotEqual(repo.retain_repo_versions, 1000)

    def test_set_only_published_and_stating_to_2000(self):
        """Only published,staging is set to 2000"""
        AnsibleRepository.objects.filter(name__in=["published", "staging"]).update(
            retain_repo_versions=1
        )
        call_command(CMD, "--yes", "--value", "2000", "--repository", "published,staging")

        for repo in AnsibleRepository.objects.filter(name__in=["published", "staging"]):
            self.assertEqual(repo.retain_repo_versions, 2000)

        for repo in AnsibleRepository.objects.exclude(name__in=["published", "staging"]):
            self.assertNotEqual(repo.retain_repo_versions, 2000)

    def test_set_all_to_10_excluding_published(self):
        """All the repos gets retain_repo_versions set to 10 except published"""
        call_command(CMD, "--yes", "--value", "10", "--repository", "*", "--exclude", "published")
        for repo in AnsibleRepository.objects.exclude(name="published"):
            self.assertEqual(repo.retain_repo_versions, 10)
        published = AnsibleRepository.objects.get(name="published")
        self.assertNotEqual(published.retain_repo_versions, 10)
