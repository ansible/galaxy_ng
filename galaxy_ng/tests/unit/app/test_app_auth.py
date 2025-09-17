from unittest.mock import Mock

from django.test import override_settings

from galaxy_ng.app.auth.auth import RHIdentityAuthentication
from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import Group, User
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
        self.assertFalse(User.objects.filter(username=username))
        self.assertFalse(Group.objects.filter(name=group_name))

        # perform the authentication that creates objects
        rh_id_auth.authenticate(request)

        # check objects exist: user, group, synclist, distro
        self.assertTrue(User.objects.filter(username=username))
        self.assertTrue(Group.objects.filter(name=group_name))
