import subprocess
from unittest.mock import patch, Mock
from django.test import TestCase

from galaxy_ng.app.utils.git import get_tag_commit_date, get_tag_commit_hash


class TestGitUtils(TestCase):

    @patch('galaxy_ng.app.utils.git.subprocess.run')
    @patch('galaxy_ng.app.utils.git.tempfile.mkdtemp')
    def test_get_tag_commit_date_no_checkout_path(self, mock_mkdtemp, mock_subprocess_run):
        mock_mkdtemp.return_value = '/tmp/test_checkout'

        # Mock first subprocess call (git clone)
        mock_clone_result = Mock()
        mock_clone_result.returncode = 0

        # Mock second subprocess call (git log)
        mock_log_result = Mock()
        mock_log_result.stdout = b'2022-06-07 22:18:41 +0000\n'
        mock_log_result.returncode = 0

        mock_subprocess_run.side_effect = [mock_clone_result, mock_log_result]

        result = get_tag_commit_date('https://github.com/test/repo.git', 'v1.0.0')

        self.assertEqual(result, '2022-06-07T22:18:41')
        self.assertEqual(mock_subprocess_run.call_count, 2)

        # Verify git clone call
        mock_subprocess_run.assert_any_call(
            'git clone https://github.com/test/repo.git /tmp/test_checkout',
            shell=True
        )

        # Verify git log call
        mock_subprocess_run.assert_any_call(
            "git log -1 --format='%ci'",
            shell=True,
            cwd='/tmp/test_checkout',
            stdout=subprocess.PIPE
        )

    @patch('galaxy_ng.app.utils.git.subprocess.run')
    def test_get_tag_commit_date_with_checkout_path(self, mock_subprocess_run):
        mock_log_result = Mock()
        mock_log_result.stdout = b'2023-01-15 14:30:25 +0000\n'
        mock_log_result.returncode = 0

        mock_subprocess_run.return_value = mock_log_result

        result = get_tag_commit_date('https://github.com/test/repo.git', 'v2.0.0', '/existing/path')

        self.assertEqual(result, '2023-01-15T14:30:25')
        self.assertEqual(mock_subprocess_run.call_count, 1)

        # Verify git log call only (no clone since path provided)
        mock_subprocess_run.assert_called_once_with(
            "git log -1 --format='%ci'",
            shell=True,
            cwd='/existing/path',
            stdout=subprocess.PIPE
        )

    @patch('galaxy_ng.app.utils.git.subprocess.run')
    def test_get_tag_commit_date_different_timezone(self, mock_subprocess_run):
        mock_log_result = Mock()
        mock_log_result.stdout = b'2022-12-25 09:15:33 -0500\n'
        mock_log_result.returncode = 0

        mock_subprocess_run.return_value = mock_log_result

        result = get_tag_commit_date('https://github.com/test/repo.git', 'v3.0.0', '/some/path')

        self.assertEqual(result, '2022-12-25T09:15:33')

    @patch('galaxy_ng.app.utils.git.subprocess.run')
    @patch('galaxy_ng.app.utils.git.tempfile.mkdtemp')
    def test_get_tag_commit_hash_no_checkout_path(self, mock_mkdtemp, mock_subprocess_run):
        mock_mkdtemp.return_value = '/tmp/test_checkout'

        # Mock first subprocess call (git clone)
        mock_clone_result = Mock()
        mock_clone_result.returncode = 0

        # Mock second subprocess call (git log)
        mock_log_result = Mock()
        mock_log_result.stdout = b'a1b2c3d4e5f6789012345678901234567890abcd\n'
        mock_log_result.returncode = 0

        mock_subprocess_run.side_effect = [mock_clone_result, mock_log_result]

        result = get_tag_commit_hash('https://github.com/test/repo.git', 'v1.0.0')

        self.assertEqual(result, 'a1b2c3d4e5f6789012345678901234567890abcd')
        self.assertEqual(mock_subprocess_run.call_count, 2)

        # Verify git clone call
        mock_subprocess_run.assert_any_call(
            'git clone https://github.com/test/repo.git /tmp/test_checkout',
            shell=True
        )

        # Verify git log call
        mock_subprocess_run.assert_any_call(
            "git log -1 --format='%H'",
            shell=True,
            cwd='/tmp/test_checkout',
            stdout=subprocess.PIPE
        )

    @patch('galaxy_ng.app.utils.git.subprocess.run')
    def test_get_tag_commit_hash_with_checkout_path(self, mock_subprocess_run):
        mock_log_result = Mock()
        mock_log_result.stdout = b'def456789abcdef012345678901234567890abcde\n'
        mock_log_result.returncode = 0

        mock_subprocess_run.return_value = mock_log_result

        result = get_tag_commit_hash('https://github.com/test/repo.git', 'v2.0.0', '/existing/path')

        self.assertEqual(result, 'def456789abcdef012345678901234567890abcde')
        self.assertEqual(mock_subprocess_run.call_count, 1)

        # Verify git log call only (no clone since path provided)
        mock_subprocess_run.assert_called_once_with(
            "git log -1 --format='%H'",
            shell=True,
            cwd='/existing/path',
            stdout=subprocess.PIPE
        )

    @patch('galaxy_ng.app.utils.git.subprocess.run')
    def test_get_tag_commit_hash_short_hash(self, mock_subprocess_run):
        mock_log_result = Mock()
        mock_log_result.stdout = b'abc123d\n'
        mock_log_result.returncode = 0

        mock_subprocess_run.return_value = mock_log_result

        result = get_tag_commit_hash('https://github.com/test/repo.git', 'v1.5.0', '/some/path')

        self.assertEqual(result, 'abc123d')
