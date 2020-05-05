from unittest import mock

from django.conf import settings
from rest_framework.test import APIClient, APITestCase

from galaxy_ng.app import models
from galaxy_ng.app.auth import auth
from galaxy_ng.app.models import auth as auth_models


API_PREFIX = settings.GALAXY_API_PATH_PREFIX.strip("/")


class BaseTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = self._create_user('test')
        self.client.force_authenticate(user=self.user)

        # Permission mock
        patcher = mock.patch.object(
            auth.RHEntitlementRequired, "has_permission", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _create_user(username):
        return auth_models.User.objects.create(username=username)

    @staticmethod
    def _create_group(scope, name, users=None):
        group = auth_models.Group.objects.create_identity(scope, name)
        if isinstance(users, auth_models.User):
            users = [users]
        group.user_set.add(*users)
        return group

    @staticmethod
    def _create_namespace(name, groups=None):
        namespace = models.Namespace.objects.create(name=name)
        if isinstance(groups, auth_models.Group):
            groups = [groups]
        namespace.groups.add(*groups)
        return namespace
