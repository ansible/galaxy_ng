from unittest import mock

from django.contrib.auth.models import Permission
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository, CollectionRemote
from pulpcore.app.util import get_prn
from pulpcore.app.util import reverse as pulp_reverse
from pulpcore.plugin.models import Task
from pulpcore.plugin.util import assign_role
from rest_framework import status
from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.tasks.repository import update_ansible_repository

from .base import BaseTestCase


# ENHANCED_INPUT_VALIDATION_ENABLED is dynaconf-backed in this codebase, so
# django.test.override_settings doesn't reliably affect it (unlike django-ansible-base's
# own test suite, which reads it via plain django.conf.settings). Patch the function
# CleanTextMixin actually calls instead -- portable regardless of the settings backend.
@mock.patch('ansible_base.lib.serializers.mixins.get_setting', return_value=True)
class TestAnsibleRepositoryViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(
            username='repo_admin', is_superuser=True)
        self.client.force_authenticate(user=self.admin_user)
        self.list_url = reverse('galaxy:api:ui:v1:repositories-list')

    def test_full_crud_cycle(self, mock_get_setting):
        # create
        response = self.client.post(self.list_url, {
            "name": "test_ansible_repo_1",
            "description": "A perfectly normal description.",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # retrieve by name (lookup_field='name')
        detail_url = reverse(
            'galaxy:api:ui:v1:repositories-detail', kwargs={'name': 'test_ansible_repo_1'})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test_ansible_repo_1')

        # list
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any(r['name'] == 'test_ansible_repo_1' for r in response.data['data']))

        # update (description only) is accepted and applied by the worker
        payload = {"description": "Updated description."}
        response = self.client.patch(detail_url, payload, format='json')
        repo = AnsibleRepository.objects.get(name='test_ansible_repo_1')
        self._apply_accepted_update(response, repo, payload)
        self.assertEqual(repo.description, "Updated description.")

        # dangerous description rejected via CleanTextMixin
        response = self.client.patch(
            detail_url, {"description": "<script>alert(1)</script>"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        # destroy dispatches pulpcore's async repository delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task', response.data)

    def test_dangerous_name_rejected_on_create(self, mock_get_setting):
        response = self.client.post(self.list_url, {
            "name": "<script>alert(1)</script>",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_duplicate_name_rejected_on_create(self, mock_get_setting):
        payload = {"name": "duplicate_ansible_repo", "description": "first"}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(AnsibleRepository.objects.filter(name='duplicate_ansible_repo').count(), 1)

    def test_db_unique_conflict_on_create_returns_400_not_500(self, mock_get_setting):
        # Race window: pre-insert check passes, DB uniqueness fails.
        AnsibleRepository.objects.create(name='race_create_repo')
        with mock.patch(
            'galaxy_ng.app.api.utils.validate_unique_pulp_resource_name',
            return_value=None,
        ):
            response = self.client.post(
                self.list_url,
                {"name": "race_create_repo", "description": "loser"},
                format='json',
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(AnsibleRepository.objects.filter(name='race_create_repo').count(), 1)

    def test_db_unique_conflict_on_rename_returns_400_not_500(self, mock_get_setting):
        AnsibleRepository.objects.create(name='race_rename_taken')
        AnsibleRepository.objects.create(name='race_rename_other')
        with mock.patch(
            'galaxy_ng.app.api.utils.validate_unique_pulp_resource_name',
            return_value=None,
        ):
            response = self.client.patch(
                self._detail_url('race_rename_other'),
                {"name": "race_rename_taken"},
                format='json',
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(AnsibleRepository.objects.filter(name='race_rename_taken').count(), 1)
        self.assertTrue(AnsibleRepository.objects.filter(name='race_rename_other').exists())

    def _detail_url(self, name):
        return reverse('galaxy:api:ui:v1:repositories-detail', kwargs={'name': name})

    def _listed_names(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [r['name'] for r in response.data['data']]

    def _task_from_href(self, task_href):
        task_pk = str(task_href).rstrip('/').split('/')[-1]
        return Task.objects.get(pk=task_pk)

    def _apply_accepted_update(self, response, repository, data, partial=True):
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        self.assertIn('task', response.data)
        update_ansible_repository(repository.pk, data, partial)
        repository.refresh_from_db()
        return repository

    def test_unprivileged_user_cannot_see_or_mutate_private_repos(self, mock_get_setting):
        AnsibleRepository.objects.create(name='public_repo_rbac', private=False)
        AnsibleRepository.objects.create(name='private_repo_rbac', private=True)
        self.client.force_authenticate(user=self.user)

        names = self._listed_names()
        self.assertIn('public_repo_rbac', names)
        self.assertNotIn('private_repo_rbac', names)

        response = self.client.get(self._detail_url('public_repo_rbac'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        private_url = self._detail_url('private_repo_rbac')
        missing_url = self._detail_url('does-not-exist-repo')
        # Same 404 as a name that does not exist: do not 403 and disclose the name.
        self.assertEqual(self.client.get(private_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(missing_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.patch(private_url, {"description": "nope"}, format='json').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(self.client.delete(private_url).status_code, status.HTTP_404_NOT_FOUND)

    def test_unprivileged_user_cannot_create_repo(self, mock_get_setting):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, {"name": "nope"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(AnsibleRepository.objects.filter(name='nope').exists())

    def test_creator_with_only_add_perm_can_update_and_delete(self, mock_get_setting):
        # add_ansiblerepository is enough to POST; the pulp creation hook must
        # then grant galaxy.ansible_repository_owner so PATCH/DELETE succeed.
        creator = auth_models.User.objects.create(username='repo_creator')
        creator.user_permissions.add(Permission.objects.get(
            content_type__app_label='ansible',
            codename='add_ansiblerepository',
        ))
        self.client.force_authenticate(user=creator)

        response = self.client.post(self.list_url, {
            "name": "owned_by_creator_repo",
            "description": "created by least-privileged user",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        detail_url = self._detail_url('owned_by_creator_repo')

        response = self.client.patch(
            detail_url, {"description": "updated by creator"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        self.assertIn('task', response.data)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        self.assertIn('task', response.data)

    def test_change_without_view_cannot_patch_private_repo(self, mock_get_setting):
        # View is only enforced on private repos; change alone must not be enough.
        AnsibleRepository.objects.create(
            name='private_change_no_view_repo', private=True)
        changer = auth_models.User.objects.create(username='repo_changer_no_view')
        changer.user_permissions.add(Permission.objects.get(
            content_type__app_label='ansible',
            codename='change_ansiblerepository',
        ))
        self.client.force_authenticate(user=changer)

        response = self.client.patch(
            self._detail_url('private_change_no_view_repo'),
            {"description": "should not apply"},
            format='json',
        )
        # No view permission → private repo is scoped out of the queryset (404,
        # not 403, so the name is not disclosed).
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        repo = AnsibleRepository.objects.get(name='private_change_no_view_repo')
        self.assertNotEqual(repo.description, "should not apply")

    def test_global_view_perm_can_retrieve_private_repo(self, mock_get_setting):
        AnsibleRepository.objects.create(name='private_global_view_repo', private=True)
        viewer = auth_models.User.objects.create(username='repo_global_viewer')
        viewer.user_permissions.add(Permission.objects.get(
            content_type__app_label='ansible',
            codename='view_ansiblerepository',
        ))
        self.client.force_authenticate(user=viewer)

        response = self.client.get(self._detail_url('private_global_view_repo'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'private_global_view_repo')

    def test_object_level_perms_allow_private_repo_access(self, mock_get_setting):
        private_repo = AnsibleRepository.objects.create(
            name='private_owned_repo', private=True)
        assign_role("galaxy.ansible_repository_owner", self.user, obj=private_repo)
        self.client.force_authenticate(user=self.user)

        self.assertIn('private_owned_repo', self._listed_names())

        detail_url = self._detail_url('private_owned_repo')
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task', response.data)

    def test_cannot_delete_repo_with_protected_base_path(self, mock_get_setting):
        # Same guard as pulp repositories/ansible/ansible destroy.
        # 'published' is created by data migrations (0017).
        response = self.client.delete(self._detail_url('published'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(AnsibleRepository.objects.filter(name='published').exists())

    def test_can_delete_repo_with_unprotected_distribution(self, mock_get_setting):
        repo = AnsibleRepository.objects.create(name='unprotected_delete_repo')
        AnsibleDistribution.objects.create(
            name='unprotected_delete_repo',
            base_path='unprotected_delete_repo',
            repository=repo,
        )
        response = self.client.delete(self._detail_url('unprotected_delete_repo'))
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task', response.data)

    def test_dotted_name_round_trips_on_detail_url(self, mock_get_setting):
        # lookup_value_regex must allow '.' — DRF's default [^/.]+ 404s these.
        response = self.client.post(self.list_url, {
            "name": "foo.bar",
            "description": "dotted name",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        detail_url = self._detail_url('foo.bar')
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['name'], 'foo.bar')

        payload = {"description": "updated dotted name"}
        response = self.client.patch(detail_url, payload, format='json')
        repo = AnsibleRepository.objects.get(name='foo.bar')
        self._apply_accepted_update(response, repo, payload)
        self.assertEqual(repo.description, 'updated dotted name')

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task', response.data)

    def test_next_version_is_read_only(self, mock_get_setting):
        response = self.client.post(self.list_url, {
            "name": "next_version_readonly_repo",
            "next_version": 99,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        repo = AnsibleRepository.objects.get(name='next_version_readonly_repo')
        self.assertNotEqual(repo.next_version, 99)

        original = repo.next_version
        payload = {"next_version": 99}
        response = self.client.patch(
            self._detail_url('next_version_readonly_repo'),
            payload,
            format='json',
        )
        self._apply_accepted_update(response, repo, payload)
        self.assertEqual(repo.next_version, original)

    def test_create_persists_pulp_form_fields(self, mock_get_setting):
        remote = CollectionRemote.objects.create(
            name='form_fields_remote',
            url='https://example.com/api/',
        )
        # Must use API_ROOT-prefixed pulp hrefs (e.g. /api/galaxy/pulp/api/v3/...).
        remote_href = pulp_reverse(
            'remotes-ansible/collection-detail', kwargs={'pk': remote.pk})
        response = self.client.post(self.list_url, {
            "name": "finance-internal",
            "description": "finance team collections",
            "private": True,
            "remote": remote_href,
            "pulp_labels": {"pipeline": "staging", "hide_from_search": ""},
            "retain_repo_versions": 3,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data['private'])
        self.assertEqual(response.data['retain_repo_versions'], 3)
        self.assertEqual(response.data['pulp_labels']['pipeline'], 'staging')
        self.assertIn('hide_from_search', response.data['pulp_labels'])
        self.assertIn('pulp_href', response.data)
        self.assertIn('repositories/ansible/ansible', response.data['pulp_href'])
        self.assertIn(str(remote.pk), response.data['remote'])

        repo = AnsibleRepository.objects.get(name='finance-internal')
        self.assertTrue(repo.private)
        self.assertEqual(repo.remote_id, remote.pk)
        self.assertEqual(repo.retain_repo_versions, 3)
        self.assertEqual(repo.pulp_labels.get('pipeline'), 'staging')

    def test_patch_private_updates_stored_value(self, mock_get_setting):
        repo = AnsibleRepository.objects.create(name='was_public_repo', private=False)
        payload = {"private": True}
        response = self.client.patch(
            self._detail_url('was_public_repo'),
            payload,
            format='json',
        )
        self._apply_accepted_update(response, repo, payload)
        self.assertTrue(repo.private)

    def test_description_only_patch_does_not_clear_private(self, mock_get_setting):
        repo = AnsibleRepository.objects.create(
            name='stays_private_repo',
            private=True,
            description='original',
        )
        payload = {"description": "updated only"}
        response = self.client.patch(
            self._detail_url('stays_private_repo'),
            payload,
            format='json',
        )
        self._apply_accepted_update(response, repo, payload)
        self.assertTrue(repo.private)
        self.assertEqual(repo.description, 'updated only')

    def test_description_patch_does_not_clobber_concurrent_repo_fields(
            self, mock_get_setting):
        # The reserved task reloads the repository after conflicting work
        # finishes, so a description-only edit must not write stale
        # next_version / private values.
        repo = AnsibleRepository.objects.create(
            name='race_next_version_repo',
            description='original',
            private=False,
        )
        original_next_version = repo.next_version
        payload = {"description": "updated after concurrent writer"}
        response = self.client.patch(
            self._detail_url('race_next_version_repo'),
            payload,
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)

        AnsibleRepository.objects.filter(pk=repo.pk).update(
            next_version=F('next_version') + 1,
            private=True,
        )
        update_ansible_repository(repo.pk, payload, partial=True)
        repo.refresh_from_db()
        self.assertEqual(repo.description, 'updated after concurrent writer')
        self.assertTrue(repo.private)
        self.assertEqual(repo.next_version, original_next_version + 1)

    def test_unknown_write_keys_are_rejected(self, mock_get_setting):
        response = self.client.post(self.list_url, {
            "name": "unknown_keys_repo",
            "not_a_field": True,
            "also_unknown": 1,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        # Galaxy wraps DRF ValidationError in {'errors': [{'source': {'parameter': ...}}]}.
        error_params = {
            err['source']['parameter']
            for err in response.data['errors']
            if err.get('source')
        }
        self.assertIn('not_a_field', error_params)
        self.assertIn('also_unknown', error_params)
        self.assertFalse(AnsibleRepository.objects.filter(name='unknown_keys_repo').exists())

    def test_get_body_can_be_put_back(self, mock_get_setting):
        create = self.client.post(self.list_url, {
            "name": "roundtrip_repo",
            "description": "round trip",
            "private": True,
        }, format='json')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED, create.data)
        detail_url = self._detail_url('roundtrip_repo')

        got = self.client.get(detail_url)
        self.assertEqual(got.status_code, status.HTTP_200_OK, got.data)
        body = got.json()
        response = self.client.put(detail_url, body, format='json')
        repo = AnsibleRepository.objects.get(name='roundtrip_repo')
        self._apply_accepted_update(response, repo, body, partial=False)
        self.assertTrue(repo.private)
        self.assertEqual(repo.description, 'round trip')

    def test_destroy_uses_pulp_repository_serializer(self, mock_get_setting):
        from galaxy_ng.app.api.ui.v1.viewsets.repository import AnsibleRepositoryViewSet
        from pulp_ansible.app.serializers import AnsibleRepositorySerializer as PulpRepoSerializer

        viewset = AnsibleRepositoryViewSet()
        viewset.action = 'destroy'
        self.assertIs(viewset.get_serializer_class(), PulpRepoSerializer)
        viewset.action = 'update'
        self.assertEqual(
            viewset.get_serializer_class().__name__,
            'AnsibleRepositoryDetailSerializer',
        )

        AnsibleRepository.objects.create(name='destroy_serializer_repo')
        response = self.client.delete(self._detail_url('destroy_serializer_repo'))
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        self.assertIn('task', response.data)

    def test_update_task_reserves_repository(self, mock_get_setting):
        repo = AnsibleRepository.objects.create(
            name='dispatch_update_repo', description='old')
        response = self.client.patch(
            self._detail_url('dispatch_update_repo'),
            {"description": "new"},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        self.assertIn('task', response.data)
        task = self._task_from_href(response.data['task'])
        self.assertIn('update_ansible_repository', task.name)
        self.assertIn(get_prn(repo), task.reserved_resources_record or [])

    def test_patch_remote_resets_last_synced_metadata_time(self, mock_get_setting):
        remote_a = CollectionRemote.objects.create(
            name='sync_skip_remote_a', url='https://a.example.com/api/')
        remote_b = CollectionRemote.objects.create(
            name='sync_skip_remote_b', url='https://b.example.com/api/')
        repo = AnsibleRepository.objects.create(
            name='sync_skip_repo',
            remote=remote_a,
            last_synced_metadata_time=timezone.now(),
        )
        remote_href = pulp_reverse(
            'remotes-ansible/collection-detail', kwargs={'pk': remote_b.pk})
        payload = {"remote": remote_href}
        response = self.client.patch(
            self._detail_url('sync_skip_repo'), payload, format='json')
        self._apply_accepted_update(response, repo, payload)
        self.assertEqual(repo.remote_id, remote_b.pk)
        self.assertIsNone(repo.last_synced_metadata_time)

    def test_patch_retain_repo_versions_is_saved(self, mock_get_setting):
        repo = AnsibleRepository.objects.create(
            name='retain_versions_repo', retain_repo_versions=5)
        payload = {"retain_repo_versions": 1}
        response = self.client.patch(
            self._detail_url('retain_versions_repo'), payload, format='json')
        self._apply_accepted_update(response, repo, payload)
        self.assertEqual(repo.retain_repo_versions, 1)

