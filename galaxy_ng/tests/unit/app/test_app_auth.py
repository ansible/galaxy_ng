from unittest.mock import Mock

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository
from pulpcore.plugin.models.role import Role

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
        group = Group.objects.get(name=group_name)
        synclist = SyncList.objects.get(name=synclist_name)
        distro = AnsibleDistribution.objects.get(name=synclist_name)
        self.assertEqual(synclist.distribution, distro)

        # test rbac: check group is linked to expected role
        self.assertEqual(group.object_roles.all().count(), 1)
        group_role = group.object_roles.all().first()
        synclist_owner_role = Role.objects.get(name="galaxy.synclist_owner")
        self.assertEqual(group_role.role, synclist_owner_role)

        # test rbac: check group is linked to expected object
        self.assertEqual(str(synclist.id), group_role.object_id)
        ct = ContentType.objects.get(id=group_role.content_type_id)
        self.assertEqual(ct.model, "synclist")

        # assert objects do not exist: repo
        self.assertFalse(AnsibleRepository.objects.filter(name=synclist_name))
