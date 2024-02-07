from django.test import TestCase

from galaxy_ng.app.models import Organization, Team


class TestOrganizationModels(TestCase):
    def test_org_create(self):
        org = Organization.objects.create(name="TestOrg1", description="A test organization.")
        assert org.group.name == "org::TestOrg1"

    def test_team_create(self):
        org1 = Organization.objects.create(name="TestOrg1", description="A test organization.")
        org2 = Organization.objects.create(name="TestOrg2", description="A test organization.")

        team1 = Team.objects.create(name="TestTeam1", organization=org1)
        assert team1.group.name == f"team:{org1.id}::TestTeam1"
        team2 = Team.objects.create(name="TestTeam2", organization=org2)
        assert team2.group.name == f"team:{org2.id}::TestTeam2"
