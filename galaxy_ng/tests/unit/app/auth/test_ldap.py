from unittest.mock import Mock, patch
from django.test import TestCase

from galaxy_ng.app.auth.ldap import GalaxyLDAPSettings, GalaxyLDAPBackend, PrefixedLDAPBackend


class TestGalaxyLDAPSettings(TestCase):

    def setUp(self):
        self.settings = GalaxyLDAPSettings('AUTH_LDAP_', {})

    @patch('galaxy_ng.app.auth.ldap.Group')
    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_mirror_groups_with_existing_groups_disabled(self, mock_settings, mock_group):
        mock_settings.get.return_value = False
        self.settings._mirror_groups = {'ldap_group1', 'ldap_group2'}

        result = self.settings.MIRROR_GROUPS

        assert result == {'ldap_group1', 'ldap_group2'}
        mock_group.objects.all.assert_not_called()

    @patch('galaxy_ng.app.auth.ldap.Group')
    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_mirror_groups_with_existing_groups_enabled_no_cached(self, mock_settings, mock_group):
        mock_settings.get.return_value = True
        self.settings._mirror_groups = {'ldap_group1', 'ldap_group2'}
        self.settings._cached_groups = None

        mock_queryset = Mock()
        mock_queryset.values_list.return_value = ['db_group1', 'db_group2']
        mock_group.objects.all.return_value = mock_queryset

        result = self.settings.MIRROR_GROUPS

        assert result == {'ldap_group1', 'ldap_group2', 'db_group1', 'db_group2'}
        mock_group.objects.all.assert_called_once()
        mock_queryset.values_list.assert_called_once_with('name', flat=True)

    @patch('galaxy_ng.app.auth.ldap.Group')
    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_mirror_groups_with_existing_groups_enabled_cached(self, mock_settings, mock_group):
        mock_settings.get.return_value = True
        self.settings._mirror_groups = {'ldap_group1', 'ldap_group2'}
        self.settings._cached_groups = {'cached_group1', 'cached_group2'}

        result = self.settings.MIRROR_GROUPS

        assert result == {'ldap_group1', 'ldap_group2', 'cached_group1', 'cached_group2'}
        mock_group.objects.all.assert_not_called()

    @patch('galaxy_ng.app.auth.ldap.Group')
    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_mirror_groups_with_existing_groups_enabled_no_mirror_groups(
        self, mock_settings, mock_group
    ):
        mock_settings.get.return_value = True
        self.settings._mirror_groups = None
        self.settings._cached_groups = None

        mock_queryset = Mock()
        mock_queryset.values_list.return_value = ['db_group1', 'db_group2']
        mock_group.objects.all.return_value = mock_queryset

        result = self.settings.MIRROR_GROUPS

        assert result == {'db_group1', 'db_group2'}
        mock_group.objects.all.assert_called_once()

    @patch('galaxy_ng.app.auth.ldap.Group')
    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_mirror_groups_with_existing_groups_enabled_frozenset_mirror_groups(
        self, mock_settings, mock_group
    ):
        mock_settings.get.return_value = True
        self.settings._mirror_groups = frozenset({'ldap_group1'})
        self.settings._cached_groups = None

        mock_queryset = Mock()
        mock_queryset.values_list.return_value = ['db_group1']
        mock_group.objects.all.return_value = mock_queryset

        result = self.settings.MIRROR_GROUPS

        assert result == {'ldap_group1', 'db_group1'}

    def test_mirror_groups_setter(self):
        test_groups = {'group1', 'group2'}

        self.settings.MIRROR_GROUPS = test_groups

        assert self.settings._mirror_groups == test_groups

    def test_mirror_groups_setter_none(self):
        self.settings.MIRROR_GROUPS = None

        assert self.settings._mirror_groups is None

    @patch('galaxy_ng.app.auth.ldap.log')
    @patch('galaxy_ng.app.auth.ldap.Group')
    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_mirror_groups_logs_cached_groups(self, mock_settings, mock_group, mock_log):
        mock_settings.get.return_value = False
        self.settings._cached_groups = {'cached1', 'cached2'}
        self.settings._mirror_groups = {'mirror1'}

        self.settings.MIRROR_GROUPS  # noqa: B018

        mock_log.debug.assert_called_once_with(
            "Cached LDAP groups: %s", str({'cached1', 'cached2'})
        )


class TestGalaxyLDAPBackend(TestCase):

    def setUp(self):
        self.backend = GalaxyLDAPBackend()

    def test_init_creates_galaxy_ldap_settings(self):
        backend = GalaxyLDAPBackend()

        assert isinstance(backend.settings, GalaxyLDAPSettings)


class TestPrefixedLDAPBackend(TestCase):

    def setUp(self):
        self.backend = PrefixedLDAPBackend()

    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_prefix_property(self, mock_settings):
        mock_settings.get.return_value = 'imported_'

        result = self.backend.prefix

        assert result == 'imported_'
        mock_settings.get.assert_called_once_with('RENAMED_USERNAME_PREFIX')

    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_authenticate_removes_prefix(self, mock_settings):
        mock_settings.get.return_value = 'imported_'

        with patch.object(GalaxyLDAPBackend, 'authenticate') as mock_super_auth:
            mock_super_auth.return_value = Mock()

            self.backend.authenticate(username='imported_testuser', password='pass')

            mock_super_auth.assert_called_once_with(username='testuser', password='pass')

    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_authenticate_no_prefix(self, mock_settings):
        mock_settings.get.return_value = 'imported_'

        with patch.object(GalaxyLDAPBackend, 'authenticate') as mock_super_auth:
            mock_super_auth.return_value = Mock()

            self.backend.authenticate(username='testuser', password='pass')

            mock_super_auth.assert_called_once_with(username='testuser', password='pass')

    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_authenticate_no_username(self, mock_settings):
        mock_settings.get.return_value = 'imported_'

        with patch.object(GalaxyLDAPBackend, 'authenticate') as mock_super_auth:
            mock_super_auth.return_value = Mock()

            self.backend.authenticate(password='pass')

            mock_super_auth.assert_called_once_with(password='pass')

    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_authenticate_username_none(self, mock_settings):
        mock_settings.get.return_value = 'imported_'

        with patch.object(GalaxyLDAPBackend, 'authenticate') as mock_super_auth:
            mock_super_auth.return_value = Mock()

            self.backend.authenticate(username=None, password='pass')

            mock_super_auth.assert_called_once_with(username=None, password='pass')

    @patch('galaxy_ng.app.auth.ldap.User')
    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_get_or_build_user_no_prefix_no_prefixed_user(self, mock_settings, mock_user):
        mock_settings.get.return_value = 'imported_'
        mock_queryset = Mock()
        mock_queryset.__bool__ = Mock(return_value=False)
        mock_user.objects.filter.return_value = mock_queryset
        mock_ldap_user = Mock()

        with patch.object(GalaxyLDAPBackend, 'get_or_build_user') as mock_super_get:
            mock_super_get.return_value = Mock()

            self.backend.get_or_build_user('testuser', mock_ldap_user)

            mock_user.objects.filter.assert_called_once_with(username='imported_testuser')
            mock_super_get.assert_called_once_with('testuser', mock_ldap_user)

    @patch('galaxy_ng.app.auth.ldap.User')
    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_get_or_build_user_no_prefix_with_prefixed_user(self, mock_settings, mock_user):
        mock_settings.get.return_value = 'imported_'
        mock_queryset = Mock()
        mock_queryset.__bool__ = Mock(return_value=True)
        mock_user.objects.filter.return_value = mock_queryset
        mock_ldap_user = Mock()

        with patch.object(GalaxyLDAPBackend, 'get_or_build_user') as mock_super_get:
            mock_super_get.return_value = Mock()

            self.backend.get_or_build_user('testuser', mock_ldap_user)

            mock_user.objects.filter.assert_called_once_with(username='imported_testuser')
            mock_super_get.assert_called_once_with('imported_testuser', mock_ldap_user)

    @patch('galaxy_ng.app.auth.ldap.User')
    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_get_or_build_user_with_prefix(self, mock_settings, mock_user):
        mock_settings.get.return_value = 'imported_'
        mock_ldap_user = Mock()

        with patch.object(GalaxyLDAPBackend, 'get_or_build_user') as mock_super_get:
            mock_super_get.return_value = Mock()

            self.backend.get_or_build_user('imported_testuser', mock_ldap_user)

            mock_user.objects.filter.assert_not_called()
            mock_super_get.assert_called_once_with('imported_testuser', mock_ldap_user)

    @patch('galaxy_ng.app.auth.ldap.User')
    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_get_or_build_user_partial_prefix_match(self, mock_settings, mock_user):
        mock_settings.get.return_value = 'imported_'
        mock_user.objects.filter.return_value.__bool__ = Mock(return_value=False)
        mock_ldap_user = Mock()

        with patch.object(GalaxyLDAPBackend, 'get_or_build_user') as mock_super_get:
            mock_super_get.return_value = Mock()

            # Username contains prefix but doesn't start with it
            self.backend.get_or_build_user('user_imported_name', mock_ldap_user)

            mock_super_get.assert_called_once_with('user_imported_name', mock_ldap_user)

    @patch('galaxy_ng.app.auth.ldap.User')
    @patch('galaxy_ng.app.auth.ldap.settings')
    def test_get_or_build_user_empty_username(self, mock_settings, mock_user):
        mock_settings.get.return_value = 'imported_'
        mock_queryset = Mock()
        mock_queryset.__bool__ = Mock(return_value=False)
        mock_user.objects.filter.return_value = mock_queryset
        mock_ldap_user = Mock()

        with patch.object(GalaxyLDAPBackend, 'get_or_build_user') as mock_super_get:
            mock_super_get.return_value = Mock()

            self.backend.get_or_build_user('', mock_ldap_user)

            mock_user.objects.filter.assert_called_once_with(username='imported_')
            mock_super_get.assert_called_once_with('', mock_ldap_user)
