import logging
from rest_framework import status
from django.test import override_settings

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app import models
from pulp_container.app import models as container_models

from galaxy_ng.app.constants import DeploymentMode

from .base import BaseTestCase, get_current_ui_url

log = logging.getLogger(__name__)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestContainerRemote(BaseTestCase):
    def setUp(self):
        super().setUp()
        roles = ['galaxy.execution_environment_admin']
        self.container_user = auth_models.User.objects.create(username='container_user')
        self.admin = auth_models.User.objects.create(username='admin', is_superuser=True)
        self.regular_user = auth_models.User.objects.create(username='hacker')
        self.container_user.save()
        self.registry = models.ContainerRegistryRemote.objects.create(
            name="Test Registry",
            url="quay.io",
            proxy_url="example.com",
            username="foo",
            password="bar"
        )
        self.registry2 = models.ContainerRegistryRemote.objects.create(
            name="Test registry 2",
            url="registry.redhat.io",
        )
        self.remote_list_url = get_current_ui_url('execution-environments-remote-list')
        self.container_group = self._create_group(
            "",
            "container_group",
            users=[self.container_user, ],
            roles=roles
        )

    def _create_remote(self, user, name, registry_pk, **kwargs):
        self.client.force_authenticate(user=user)
        return self.client.post(
            self.remote_list_url,
            {"name": name, "upstream_name": "foo", "registry": registry_pk, **kwargs},
            format='json'
        )

    def _update_remote(self, remote_pk, user, payload):
        self.client.force_authenticate(user=user)
        return self.client.put(
            f"{self.remote_list_url}{remote_pk}/",
            payload,
            format='json'
        )

    def _error_has_message(self, response, message, expected_errors=None, expected_field=None):
        """
        Checks that:
            1. the response object has an errors field
            2. that the given message matches one of the fields
            4. (optional) that the error matching the message is from the expected field
            3. (optional) that the number of errors is equal to expected_errors
        """
        errors = response.data.get('errors', None)
        self.assertTrue(errors is not None)

        if expected_errors:
            self.assertEqual(len(errors), expected_errors)

        for error in errors:
            if message.lower() in error["detail"].lower():
                if expected_field:
                    self.assertEqual(error['source']['parameter'], expected_field)
                return True

        return False

    def test_remote_creation(self):
        # test unprivileged users can't create
        response = self._create_remote(self.regular_user, 'remote/remote_repo2', self.registry.pk)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self._create_remote(self.container_user, 'remote/remote_repo', self.registry.pk)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # test values are copied over from registy
        remote_obj = container_models.ContainerRemote.objects.get(pk=response.data['pulp_id'])
        self.assertEqual(remote_obj.url, self.registry.url)
        self.assertEqual(remote_obj.proxy_url, self.registry.proxy_url)
        self.assertEqual(remote_obj.password, self.registry.password)
        self.assertEqual(remote_obj.registry.registry.pk, self.registry.pk)

        # test associated objects are created
        self.assertEqual(
            container_models.ContainerRepository.objects.filter(remote=remote_obj).count(), 1)
        repo = container_models.ContainerRepository.objects.filter(remote=remote_obj).first()

        self.assertEqual(repo.name, remote_obj.name)

        self.assertEqual(container_models.Distribution.objects.filter(repository=repo).count(), 1)
        distro = container_models.Distribution.objects.filter(repository=repo).first()
        self.assertEqual(distro.name, remote_obj.name)

        # test duplicate names not allowed
        bad_response = self._create_remote(
            self.container_user, 'remote/remote_repo', self.registry.pk)
        self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            self._error_has_message(bad_response, "must be unique", expected_field="name"))

    def test_remote_update(self):
        response = self._create_remote(self.admin, 'remote/remote_repo', self.registry.pk)
        obj_data = response.data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        remote_pk = response.data['pulp_id']

        # test unpriviliged users can't update
        response = self._update_remote(
            remote_pk, self.regular_user, {**obj_data, "upstream_name": "streamy"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # test priviledged users can update
        response = self._update_remote(
            remote_pk,
            self.container_user,
            {**obj_data, "upstream_name": "streamy", "registry": self.registry2.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # test values are copied over from registy
        remote_obj = container_models.ContainerRemote.objects.get(pk=remote_pk)
        self.assertEqual(remote_obj.url, self.registry2.url)
        self.assertEqual(remote_obj.proxy_url, self.registry2.proxy_url)
        self.assertEqual(remote_obj.password, self.registry2.password)
        self.assertEqual(remote_obj.registry.registry.pk, self.registry2.pk)

        # test changing name not allowed
        response = self._update_remote(
            remote_pk,
            self.container_user,
            {**obj_data, "name": "my_new_name"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(self._error_has_message(
            response, "cannot be changed", expected_field="name"))

    def test_remote_update_after_registry_deletion(self):
        """Ensure that a remote can be updated after the registry it's associated with is deleted

        1. create a registry
        2. create a remote in the registry
        3. delete the registry
        4. attempt to update the remote to use a new registry
        """
        # 1
        registry = models.ContainerRegistryRemote.objects.create(
            name="Test registry 3",
            url="docker.io",
        )

        # 2
        response = self._create_remote(self.admin, 'remote3/remote_repo3', registry.pk)
        obj_data = response.data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        remote_pk = response.data['pulp_id']

        # 3
        registry.delete()

        # connection has been deleted
        self.assertFalse(
            models.container.ContainerRegistryRepos.objects.filter(
                registry=registry,
                repository_remote__pk=remote_pk
            ).exists()
        )

        # 4
        new_registry = models.ContainerRegistryRemote.objects.create(
            name="Test registry 4",
            url="myregistry.io",
        )

        # test update after registry deletion
        response = self._update_remote(
            remote_pk,
            self.container_user,
            {**obj_data, "upstream_name": "streamy", "registry": new_registry.pk}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # connection has been re-created
        self.assertTrue(
            models.container.ContainerRegistryRepos.objects.filter(
                registry=new_registry,
                repository_remote__pk=remote_pk
            ).exists()
        )

    def test_validation(self):
        # test invalid registry
        response = self._create_remote(
            self.container_user,
            "hello/i/am/invalid",
            "e47d47a9-30ea-4dd8-bebf-908893f59880"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(self._error_has_message(
            response, "registry does not exist", expected_field="registry"))
        self.assertTrue(self._error_has_message(
            response, "names can only contain alphanumeric", expected_field="name"))

    def test_excludes_default(self):
        response = self._create_remote(
            self.admin, 'remote/remote_repo', self.registry.pk, exclude_tags=["foo"])
        obj_data = response.data

        self.assertTrue("*-source" in obj_data["exclude_tags"])
        self.assertEqual(len(obj_data["exclude_tags"]), 2)

        # verify exclude source can be removed.
        response = self._update_remote(
            obj_data['pulp_id'],
            self.container_user,
            {**obj_data, "exclude_tags": ["foo"]}
        )

        obj_data = response.data

        self.assertTrue("*-source" not in obj_data["exclude_tags"])
        self.assertEqual(len(obj_data["exclude_tags"]), 1)
