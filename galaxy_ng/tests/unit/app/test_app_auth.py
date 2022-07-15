from unittest.mock import Mock

from django.test import override_settings
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository

from galaxy_ng.app.auth.auth import RHIdentityAuthentication
from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import Group, SyncList, User
from galaxy_ng.tests.unit.api import rh_auth as rh_auth_utils
from galaxy_ng.tests.unit.api.base import BaseTestCase


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value)
class TestRHIdentityAuth(BaseTestCase):
    def test_authenticate(self):
        # user setup
        username = "user_testing_rh_auth"
        account_number = "22446688"
        x_rh_identity = rh_auth_utils.user_x_rh_identity(username, account_number)
        request = Mock()
        request.META = {"HTTP_X_RH_IDENTITY": x_rh_identity}
        rh_id_auth = RHIdentityAuthentication()

        # assert objects do not exist: user, group, synclist, distro, repo
        group_name = f"rh-identity-account:{account_number}"
        synclist_name = f"{account_number}-synclist"
        self.assertFalse(User.objects.filter(username=username))
        self.assertFalse(Group.objects.filter(name=group_name))
        self.assertFalse(SyncList.objects.filter(name=synclist_name))
        self.assertFalse(AnsibleRepository.objects.filter(name=synclist_name))
        self.assertFalse(AnsibleDistribution.objects.filter(name=synclist_name))

        # perform the authentication that creates objects
        rh_id_auth.authenticate(request)

        # check objects exist: user, group, synclist, distro
        User.objects.get(username=username)
        Group.objects.get(name=group_name)
        synclist = SyncList.objects.get(name=synclist_name)
        distro = AnsibleDistribution.objects.get(name=synclist_name)
        self.assertEqual(synclist.distribution, distro)

        # assert objects do not exist: repo
        self.assertFalse(AnsibleRepository.objects.filter(name=synclist_name))
