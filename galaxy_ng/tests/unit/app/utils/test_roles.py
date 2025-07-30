import datetime
from unittest.mock import patch, Mock, mock_open
import yaml

from django.test import TestCase
from galaxy_ng.app.utils.roles import (
    get_path_git_root,
    get_path_head_date,
    get_path_role_repository,
    get_path_role_meta,
    get_path_role_name,
    get_path_role_namespace,
    get_path_role_version,
    path_is_role,
    make_runtime_yaml,
    get_path_galaxy_key,
    set_path_galaxy_key,
    set_path_galaxy_version,
    set_path_galaxy_repository,
    _clean_role_name
)


class TestGitUtilities(TestCase):

    @patch('galaxy_ng.app.utils.roles.subprocess.run')
    def test_get_path_git_root(self, mock_run):
        mock_result = Mock()
        mock_result.stdout.decode.return_value = '/home/user/project\n'
        mock_run.return_value = mock_result

        result = get_path_git_root('/some/path')
        assert result == '/home/user/project'
        mock_run.assert_called_once_with(
            'git rev-parse --show-toplevel',
            cwd='/some/path',
            shell=True,
            stdout=-1
        )

    @patch('galaxy_ng.app.utils.roles.subprocess.run')
    def test_get_path_head_date(self, mock_run):
        mock_result = Mock()
        mock_result.stdout.decode.return_value = '2021-10-31 00:03:43 -0500\n'
        mock_run.return_value = mock_result

        result = get_path_head_date('/some/path')
        expected = datetime.datetime(
            2021, 10, 31, 0, 3, 43,
            tzinfo=datetime.timezone(datetime.timedelta(hours=-5))
        )
        assert result == expected

    @patch('galaxy_ng.app.utils.roles.subprocess.run')
    def test_get_path_role_repository(self, mock_run):
        mock_result = Mock()
        mock_result.stdout.decode.return_value = 'https://github.com/user/repo.git\n'
        mock_run.return_value = mock_result

        result = get_path_role_repository('/some/path')
        assert result == 'https://github.com/user/repo.git'


class TestRoleMetadata(TestCase):

    def test_get_path_role_meta(self):
        meta_content = {
            'galaxy_info': {
                'role_name': 'test_role',
                'author': 'test_author'
            }
        }

        with patch('builtins.open', mock_open(read_data=yaml.dump(meta_content))):
            result = get_path_role_meta('/some/path')
            assert result == meta_content

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    def test_get_path_role_name_from_galaxy_yml(self, mock_get_galaxy_key):
        mock_get_galaxy_key.return_value = 'galaxy_role_name'

        result = get_path_role_name('/some/path')
        assert result == 'galaxy_role_name'

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.os.path.exists')
    def test_get_path_role_name_from_meta(self, mock_exists, mock_get_galaxy_key):
        mock_get_galaxy_key.return_value = None
        mock_exists.return_value = True

        meta_content = {
            'galaxy_info': {
                'role_name': 'meta_role_name'
            }
        }

        with patch('builtins.open', mock_open(read_data=yaml.dump(meta_content))):
            result = get_path_role_name('/some/path')
            assert result == 'meta_role_name'

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.os.path.exists')
    @patch('galaxy_ng.app.utils.roles.subprocess.run')
    def test_get_path_role_name_from_git_with_prefix_removal(
        self, mock_run, mock_exists, mock_get_galaxy_key
    ):
        mock_get_galaxy_key.return_value = None
        mock_exists.return_value = False
        mock_result = Mock()
        mock_result.stdout.decode.return_value = (
            'https://github.com/user/ansible-role-docker.git\n'
        )
        mock_run.return_value = mock_result

        result = get_path_role_name('/some/path')
        assert result == 'docker'

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.subprocess.run')
    def test_get_path_role_namespace_from_galaxy_yml(self, mock_run, mock_get_galaxy_key):
        mock_get_galaxy_key.return_value = 'galaxy_namespace'

        result = get_path_role_namespace('/some/path')
        assert result == 'galaxy_namespace'

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.subprocess.run')
    def test_get_path_role_namespace_from_git_ansible_collections(
        self, mock_run, mock_get_galaxy_key
    ):
        mock_get_galaxy_key.return_value = None
        mock_result = Mock()
        mock_result.stdout.decode.return_value = (
            'https://github.com/ansible-collections/community.general.git\n'
        )
        mock_run.return_value = mock_result

        result = get_path_role_namespace('/some/path')
        assert result == 'ansible'

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.get_path_head_date')
    def test_get_path_role_version_from_git_date(
        self, mock_get_head_date, mock_get_galaxy_key
    ):
        mock_get_galaxy_key.return_value = None
        mock_date = datetime.datetime(
            2021, 10, 31, 12, 30, 45, tzinfo=datetime.timezone.utc
        )
        mock_get_head_date.return_value = mock_date

        result = get_path_role_version('/some/path')
        assert result.startswith('1.0.0+20211031')


class TestPathDetection(TestCase):

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.glob.glob')
    def test_path_is_role_with_tasks(self, mock_glob, mock_get_galaxy_key):
        mock_get_galaxy_key.side_effect = [None, None]  # namespace, name
        mock_glob.return_value = ['/path/tasks', '/path/handlers']

        result = path_is_role('/some/path')
        assert result is True

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.glob.glob')
    def test_path_is_role_with_plugins(self, mock_glob, mock_get_galaxy_key):
        mock_get_galaxy_key.side_effect = [None, None]  # namespace, name
        mock_glob.return_value = ['/path/plugins', '/path/tasks']

        result = path_is_role('/some/path')
        assert result is False

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.glob.glob')
    def test_path_is_collection(self, mock_glob, mock_get_galaxy_key):
        mock_get_galaxy_key.side_effect = ['namespace', 'name']  # both exist

        result = path_is_role('/some/path')
        assert result is False


class TestRuntimeYaml(TestCase):

    @patch('galaxy_ng.app.utils.roles.os.path.exists')
    @patch('galaxy_ng.app.utils.roles.os.makedirs')
    def test_make_runtime_yaml_creates_directory(self, mock_makedirs, mock_exists):
        mock_exists.return_value = False

        with patch('builtins.open', mock_open()) as mock_file:
            make_runtime_yaml('/some/path')
            mock_makedirs.assert_called_once_with('/some/path/meta')
            mock_file.assert_called_once()

    @patch('galaxy_ng.app.utils.roles.os.path.exists')
    def test_make_runtime_yaml_directory_exists(self, mock_exists):
        mock_exists.return_value = True

        with patch('builtins.open', mock_open()) as mock_file:
            make_runtime_yaml('/some/path')
            mock_file.assert_called_once()


class TestGalaxyYamlOperations(TestCase):

    def test_get_path_galaxy_key_file_exists(self):
        galaxy_content = {'name': 'test_collection', 'version': '1.0.0'}

        with patch('galaxy_ng.app.utils.roles.os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=yaml.dump(galaxy_content))):
            result = get_path_galaxy_key('/some/path', 'name')
            assert result == 'test_collection'

    @patch('galaxy_ng.app.utils.roles.os.path.exists')
    def test_get_path_galaxy_key_file_not_exists(self, mock_exists):
        mock_exists.return_value = False

        result = get_path_galaxy_key('/some/path', 'name')
        assert result is None

    def test_set_path_galaxy_key(self):
        original_content = {'name': 'old_name', 'version': '1.0.0'}

        mock_file = mock_open(read_data=yaml.dump(original_content))
        with patch('builtins.open', mock_file):
            set_path_galaxy_key('/some/path', 'name', 'new_name')

            # Check that file was written with updated content
            written_calls = list(mock_file().write.call_args_list)
            assert len(written_calls) > 0

    def test_set_path_galaxy_version(self):
        with patch('galaxy_ng.app.utils.roles.set_path_galaxy_key') as mock_set_key:
            set_path_galaxy_version('/some/path', '2.0.0')
            mock_set_key.assert_called_once_with('/some/path', 'version', '2.0.0')

    def test_set_path_galaxy_repository(self):
        with patch('galaxy_ng.app.utils.roles.set_path_galaxy_key') as mock_set_key:
            set_path_galaxy_repository(
                '/some/path', 'https://github.com/user/repo'
            )
            mock_set_key.assert_called_once_with(
                '/some/path', 'repository', 'https://github.com/user/repo'
            )


class TestRoleNameTransformations(TestCase):

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.os.path.exists')
    @patch('galaxy_ng.app.utils.roles.subprocess.run')
    def test_role_name_dot_to_underscore(
        self, mock_run, mock_exists, mock_get_galaxy_key
    ):
        mock_get_galaxy_key.return_value = None
        mock_exists.return_value = False
        mock_result = Mock()
        mock_result.stdout.decode.return_value = (
            'https://github.com/user/docker.ubuntu.git\n'
        )
        mock_run.return_value = mock_result

        result = get_path_role_name('/some/path')
        assert result == 'docker_ubuntu'

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.os.path.exists')
    @patch('galaxy_ng.app.utils.roles.subprocess.run')
    def test_role_name_dash_to_underscore(
        self, mock_run, mock_exists, mock_get_galaxy_key
    ):
        mock_get_galaxy_key.return_value = None
        mock_exists.return_value = False
        mock_result = Mock()
        mock_result.stdout.decode.return_value = (
            'https://github.com/user/update-management.git\n'
        )
        mock_run.return_value = mock_result

        result = get_path_role_name('/some/path')
        assert result == 'update_management'


class TestCleanRoleName(TestCase):

    def test_clean_role_name_removes_git_suffix(self):
        result = _clean_role_name('my-role.git')
        assert result == 'my_role'

    def test_clean_role_name_removes_ansible_role_prefix(self):
        result = _clean_role_name('ansible-role-docker')
        assert result == 'docker'

    def test_clean_role_name_removes_ansible_prefix(self):
        result = _clean_role_name('ansible-nginx')
        assert result == 'nginx'

    def test_clean_role_name_removes_ansible_suffix(self):
        result = _clean_role_name('docker-ansible')
        assert result == 'docker'

    def test_clean_role_name_removes_ansible_dot_prefix(self):
        result = _clean_role_name('ansible.mysql')
        assert result == 'mysql'

    def test_clean_role_name_normalizes_dots_and_dashes(self):
        result = _clean_role_name('my.complex-role')
        assert result == 'my_complex_role'

    def test_clean_role_name_complex_scenario(self):
        result = _clean_role_name('ansible-role-docker.ubuntu-ansible.git')
        assert result == 'docker_ubuntu'

    def test_clean_role_name_no_changes_needed(self):
        result = _clean_role_name('simple_role')
        assert result == 'simple_role'


class TestMissingEdgeCases(TestCase):

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.subprocess.run')
    def test_get_path_role_namespace_regular_user(self, mock_run, mock_get_galaxy_key):
        mock_get_galaxy_key.return_value = None
        mock_result = Mock()
        mock_result.stdout.decode.return_value = (
            'https://github.com/regularuser/some-role.git\n'
        )
        mock_run.return_value = mock_result

        result = get_path_role_namespace('/some/path')
        assert result == 'regularuser'

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    def test_get_path_role_version_from_galaxy_yml(self, mock_get_galaxy_key):
        mock_get_galaxy_key.return_value = '2.5.0'

        result = get_path_role_version('/some/path')
        assert result == '2.5.0'

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.glob.glob')
    def test_path_is_role_with_library(self, mock_glob, mock_get_galaxy_key):
        mock_get_galaxy_key.side_effect = [None, None]  # namespace, name
        mock_glob.return_value = ['/path/library', '/path/vars']

        result = path_is_role('/some/path')
        assert result is True

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.glob.glob')
    def test_path_is_role_with_handlers(self, mock_glob, mock_get_galaxy_key):
        mock_get_galaxy_key.side_effect = [None, None]  # namespace, name
        mock_glob.return_value = ['/path/handlers', '/path/vars']

        result = path_is_role('/some/path')
        assert result is True

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.glob.glob')
    def test_path_is_role_with_defaults(self, mock_glob, mock_get_galaxy_key):
        mock_get_galaxy_key.side_effect = [None, None]  # namespace, name
        mock_glob.return_value = ['/path/defaults', '/path/vars']

        result = path_is_role('/some/path')
        assert result is True

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.glob.glob')
    def test_path_is_role_no_indicators(self, mock_glob, mock_get_galaxy_key):
        mock_get_galaxy_key.side_effect = [None, None]  # namespace, name
        mock_glob.return_value = ['/path/README.md', '/path/LICENSE']

        result = path_is_role('/some/path')
        assert result is False

    def test_get_path_galaxy_key_missing_key(self):
        galaxy_content = {'name': 'test_collection', 'version': '1.0.0'}

        with patch('galaxy_ng.app.utils.roles.os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=yaml.dump(galaxy_content))):
            result = get_path_galaxy_key('/some/path', 'description')
            assert result is None


class TestErrorHandling(TestCase):

    @patch('galaxy_ng.app.utils.roles.os.path.exists')
    def test_get_path_role_meta_file_not_found(self, mock_exists):
        mock_exists.return_value = False

        with patch('builtins.open', side_effect=FileNotFoundError), \
             self.assertRaises(FileNotFoundError):  # noqa: PT027
            get_path_role_meta('/nonexistent/path')

    @patch('galaxy_ng.app.utils.roles.get_path_galaxy_key')
    @patch('galaxy_ng.app.utils.roles.os.path.exists')
    def test_get_path_role_name_meta_file_missing_role_name(
        self, mock_exists, mock_get_galaxy_key
    ):
        mock_get_galaxy_key.return_value = None
        mock_exists.return_value = True

        meta_content = {
            'galaxy_info': {
                'author': 'test_author'
                # missing role_name
            }
        }

        with patch('builtins.open', mock_open(read_data=yaml.dump(meta_content))), \
             patch('galaxy_ng.app.utils.roles.subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.stdout.decode.return_value = (
                'https://github.com/user/test-role.git\n'
            )
            mock_run.return_value = mock_result

            result = get_path_role_name('/some/path')
            assert result == 'test_role'
