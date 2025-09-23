from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from galaxy_ng.app.tasks.promotion import (
    auto_approve,
    call_auto_approve_task,
    call_move_content_task
)


class TestAutoApprove(TestCase):

    def setUp(self):
        self.src_repo_pk = 123
        self.cv_pk = "collection-version-pk"
        self.ns_pk = "namespace-pk"

        # Mock repositories
        self.published_repo1 = Mock()
        self.published_repo1.pk = 201
        self.published_repo2 = Mock()
        self.published_repo2.pk = 202

        self.staging_repo = Mock()
        self.staging_repo.pk = 301

        self.source_repo = Mock()
        self.source_repo.pk = self.src_repo_pk

        self.signing_service = Mock()
        self.signing_service.pk = "signing-service-pk"

    @patch('galaxy_ng.app.tasks.promotion.AnsibleRepository.objects.filter')
    @patch('galaxy_ng.app.tasks.promotion.AnsibleRepository.objects.get')
    @patch('galaxy_ng.app.tasks.promotion.add_and_remove')
    @patch('galaxy_ng.app.tasks.promotion.SigningService.objects.get')
    @patch('galaxy_ng.app.tasks.promotion.sign')
    @patch('galaxy_ng.app.tasks.promotion.dispatch')
    @override_settings(GALAXY_AUTO_SIGN_COLLECTIONS=False)
    def test_auto_approve_without_signing(
        self, mock_dispatch, mock_sign, mock_signing_service_get,
        mock_add_and_remove, mock_repo_get, mock_repo_filter
    ):
        # Setup repositories
        published_queryset = Mock()
        published_queryset.values_list.return_value = [201, 202]
        staging_queryset = Mock()
        staging_queryset.values_list.return_value = [301]

        def filter_side_effect(pulp_labels__pipeline):
            if pulp_labels__pipeline == "approved":
                return published_queryset
            elif pulp_labels__pipeline == "staging":
                return staging_queryset
            return Mock()

        mock_repo_filter.side_effect = filter_side_effect
        mock_repo_get.return_value = self.source_repo

        # Source repo is in staging
        self.source_repo.pk = 301

        auto_approve(self.src_repo_pk, self.cv_pk, self.ns_pk)

        # Verify add_and_remove was called
        mock_add_and_remove.assert_called_once()

        # Verify signing was NOT called
        mock_signing_service_get.assert_not_called()
        mock_sign.assert_not_called()

        # Verify dispatch was called for move_collection
        mock_dispatch.assert_called_once()

    @patch('galaxy_ng.app.tasks.promotion.AnsibleRepository.objects.filter')
    @patch('galaxy_ng.app.tasks.promotion.AnsibleRepository.objects.get')
    @patch('galaxy_ng.app.tasks.promotion.add_and_remove')
    @patch('galaxy_ng.app.tasks.promotion.dispatch')
    def test_auto_approve_without_namespace(
        self, mock_dispatch, mock_add_and_remove, mock_repo_get, mock_repo_filter
    ):
        # Setup repositories
        published_queryset = Mock()
        published_queryset.values_list.return_value = [201, 202]
        staging_queryset = Mock()
        staging_queryset.values_list.return_value = [301]

        def filter_side_effect(pulp_labels__pipeline):
            if pulp_labels__pipeline == "approved":
                return published_queryset
            elif pulp_labels__pipeline == "staging":
                return staging_queryset
            return Mock()

        mock_repo_filter.side_effect = filter_side_effect
        mock_repo_get.return_value = self.source_repo

        # Source repo is in staging
        self.source_repo.pk = 301

        auto_approve(self.src_repo_pk, self.cv_pk, ns_pk=None)

        # Verify add_and_remove was called with only collection version
        mock_add_and_remove.assert_called_once_with(
            self.src_repo_pk,
            add_content_units=[self.cv_pk],
            remove_content_units=[]
        )

    @patch('galaxy_ng.app.tasks.promotion.AnsibleRepository.objects.filter')
    @patch('galaxy_ng.app.tasks.promotion.AnsibleRepository.objects.get')
    @patch('galaxy_ng.app.tasks.promotion.add_and_remove')
    @patch('galaxy_ng.app.tasks.promotion.dispatch')
    def test_auto_approve_source_not_in_staging(
        self, mock_dispatch, mock_add_and_remove, mock_repo_get, mock_repo_filter
    ):
        # Setup repositories
        published_queryset = Mock()
        published_queryset.values_list.return_value = [201, 202]
        staging_queryset = Mock()
        staging_queryset.values_list.return_value = [301]  # Source repo is NOT in staging

        def filter_side_effect(pulp_labels__pipeline):
            if pulp_labels__pipeline == "approved":
                return published_queryset
            elif pulp_labels__pipeline == "staging":
                return staging_queryset
            return Mock()

        mock_repo_filter.side_effect = filter_side_effect
        mock_repo_get.return_value = self.source_repo

        # Source repo is NOT in staging (different pk)
        self.source_repo.pk = 999

        auto_approve(self.src_repo_pk, self.cv_pk, self.ns_pk)

        # Verify add_and_remove was called
        mock_add_and_remove.assert_called_once()

        # Verify dispatch was NOT called (no move to published repos)
        mock_dispatch.assert_not_called()


class TestCallAutoApproveTask(TestCase):

    def setUp(self):
        self.collection_version = Mock()
        self.collection_version.pk = "cv-pk"
        self.repo = Mock()
        self.repo.pk = 123
        self.ns_pk = "ns-pk"

    @patch('galaxy_ng.app.tasks.promotion.TaskGroup.current')
    @patch('galaxy_ng.app.tasks.promotion.dispatch')
    def test_call_auto_approve_task(self, mock_dispatch, mock_task_group_current):
        mock_task_group = Mock()
        mock_task_group_current.return_value = mock_task_group
        mock_task = Mock()
        mock_dispatch.return_value = mock_task

        result = call_auto_approve_task(self.collection_version, self.repo, self.ns_pk)

        mock_task_group_current.assert_called_once()
        mock_dispatch.assert_called_once()

        # Check dispatch arguments
        call_args = mock_dispatch.call_args
        self.assertEqual(call_args[0][0].__name__, 'auto_approve')
        self.assertEqual(call_args[1]['exclusive_resources'], [self.repo])
        self.assertEqual(call_args[1]['task_group'], mock_task_group)
        self.assertEqual(call_args[1]['kwargs'], {
            'cv_pk': 'cv-pk',
            'src_repo_pk': 123,
            'ns_pk': 'ns-pk'
        })

        mock_task_group.finish.assert_called_once()
        self.assertEqual(result, mock_task)

    @patch('galaxy_ng.app.tasks.promotion.TaskGroup.current')
    @patch('galaxy_ng.app.tasks.promotion.dispatch')
    def test_call_auto_approve_task_with_none_ns_pk(self, mock_dispatch, mock_task_group_current):
        mock_task_group = Mock()
        mock_task_group_current.return_value = mock_task_group
        mock_task = Mock()
        mock_dispatch.return_value = mock_task

        call_auto_approve_task(self.collection_version, self.repo, None)

        # Check that ns_pk is passed as None
        call_args = mock_dispatch.call_args
        self.assertEqual(call_args[1]['kwargs']['ns_pk'], None)


class TestCallMoveContentTask(TestCase):

    def setUp(self):
        self.collection_version = Mock()
        self.collection_version.pk = "cv-pk"
        self.source_repo = Mock()
        self.source_repo.pk = 123
        self.dest_repo = Mock()
        self.dest_repo.pk = 456

    @patch('galaxy_ng.app.tasks.promotion.dispatch')
    def test_call_move_content_task(self, mock_dispatch):
        mock_task = Mock()
        mock_dispatch.return_value = mock_task

        result = call_move_content_task(self.collection_version, self.source_repo, self.dest_repo)

        mock_dispatch.assert_called_once()

        # Check dispatch arguments
        call_args = mock_dispatch.call_args
        self.assertEqual(call_args[0][0].__name__, 'move_collection')
        self.assertEqual(call_args[1]['exclusive_resources'], [self.source_repo, self.dest_repo])
        self.assertEqual(call_args[1]['kwargs'], {
            'cv_pk_list': ['cv-pk'],
            'src_repo_pk': 123,
            'dest_repo_list': [456]
        })

        self.assertEqual(result, mock_task)

    @patch('galaxy_ng.app.tasks.promotion.dispatch')
    def test_call_move_content_task_different_repos(self, mock_dispatch):
        # Test with different collection version and repositories
        different_cv = Mock()
        different_cv.pk = "different-cv-pk"
        different_source = Mock()
        different_source.pk = 789
        different_dest = Mock()
        different_dest.pk = 999

        mock_task = Mock()
        mock_dispatch.return_value = mock_task

        call_move_content_task(different_cv, different_source, different_dest)

        call_args = mock_dispatch.call_args
        self.assertEqual(call_args[1]['kwargs'], {
            'cv_pk_list': ['different-cv-pk'],
            'src_repo_pk': 789,
            'dest_repo_list': [999]
        })
