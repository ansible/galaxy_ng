import uuid
from unittest.mock import patch, Mock

from django.test import TestCase
from galaxy_ng.app.utils.galaxy import (
    upstream_role_iterator,
    uuid_to_int,
    int_to_uuid,
    generate_unverified_email,
    safe_fetch,
    paginated_results,
    find_namespace,
    get_namespace_owners_details
)


class TestGalaxyUtils(TestCase):

    def test_upstream_role_iterator_with_user(self):
        roles = []
        for _namespace, role, _versions in upstream_role_iterator(github_user="jctanner"):
            roles.append(role)
        assert sorted({x['github_user'] for x in roles}) == ['jctanner']

    def test_upstream_role_iterator_with_user_and_name(self):
        roles = []
        iterator_kwargs = {
            'github_user': 'geerlingguy',
            'role_name': 'docker'
        }
        for _namespace, role, _versions in upstream_role_iterator(**iterator_kwargs):
            roles.append(role)
        assert len(roles) == 1
        assert roles[0]['github_user'] == 'geerlingguy'
        assert roles[0]['name'] == 'docker'

    def test_upstream_role_iterator_with_limit(self):
        limit = 10
        count = 0
        for _namespace, _role, _versions in upstream_role_iterator(limit=limit):
            count += 1
        assert count == limit


class UUIDConversionTestCase(TestCase):

    def test_uuid_to_int_and_back(self):
        """Make sure uuids can become ints and then back to uuids"""
        for _i in range(1000):
            test_uuid = str(uuid.uuid4())
            test_int = uuid_to_int(test_uuid)
            reversed_uuid = int_to_uuid(test_int)
            assert test_uuid == reversed_uuid, f"{test_uuid} != {reversed_uuid}"


class TestGenerateUnverifiedEmail(TestCase):

    def test_generate_unverified_email(self):
        github_id = 12345
        result = generate_unverified_email(github_id)
        assert result == "12345@GALAXY.GITHUB.UNVERIFIED.COM"

    def test_generate_unverified_email_with_string(self):
        github_id = "67890"
        result = generate_unverified_email(github_id)
        assert result == "67890@GALAXY.GITHUB.UNVERIFIED.COM"


class TestSafeFetch(TestCase):

    @patch('galaxy_ng.app.utils.galaxy.requests.get')
    @patch('galaxy_ng.app.utils.galaxy.time.sleep')
    def test_safe_fetch_success(self, mock_sleep, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = safe_fetch('http://example.com')
        assert result == mock_response
        mock_get.assert_called_once_with('http://example.com')
        mock_sleep.assert_not_called()

    @patch('galaxy_ng.app.utils.galaxy.requests.get')
    @patch('galaxy_ng.app.utils.galaxy.time.sleep')
    def test_safe_fetch_retry_on_server_error(self, mock_sleep, mock_get):
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_get.side_effect = [mock_response_fail, mock_response_success]

        result = safe_fetch('http://example.com')
        assert result == mock_response_success
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(60)

    @patch('galaxy_ng.app.utils.galaxy.requests.get')
    @patch('galaxy_ng.app.utils.galaxy.time.sleep')
    def test_safe_fetch_max_retries(self, mock_sleep, mock_get):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = safe_fetch('http://example.com')
        assert result == mock_response
        assert mock_get.call_count == 5
        assert mock_sleep.call_count == 4


class TestPaginatedResults(TestCase):

    @patch('galaxy_ng.app.utils.galaxy.safe_fetch')
    def test_paginated_results_single_page(self, mock_safe_fetch):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [{'id': 1}, {'id': 2}],
            'next': None,
            'next_link': None
        }
        mock_safe_fetch.return_value = mock_response

        results = paginated_results('http://example.com/api/v1/test')
        assert results == [{'id': 1}, {'id': 2}]
        mock_safe_fetch.assert_called_once()

    @patch('galaxy_ng.app.utils.galaxy.safe_fetch')
    def test_paginated_results_multiple_pages(self, mock_safe_fetch):
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            'results': [{'id': 1}],
            'next': 'http://example.com/api/v1/test?page=2',
            'next_link': None
        }
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            'results': [{'id': 2}],
            'next': None,
            'next_link': None
        }
        mock_safe_fetch.side_effect = [mock_response1, mock_response2]

        results = paginated_results('http://example.com/api/v1/test')
        assert results == [{'id': 1}, {'id': 2}]
        assert mock_safe_fetch.call_count == 2

    @patch('galaxy_ng.app.utils.galaxy.safe_fetch')
    def test_paginated_results_404_breaks_loop(self, mock_safe_fetch):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_safe_fetch.return_value = mock_response

        results = paginated_results('http://example.com/api/v1/test')
        assert results == []


class TestFindNamespace(TestCase):

    @patch('galaxy_ng.app.utils.galaxy.safe_fetch')
    def test_find_namespace_by_name(self, mock_safe_fetch):
        mock_response1 = Mock()
        mock_response1.json.return_value = {
            'results': [{'id': 1, 'name': 'testns', 'summary_fields': {}}]
        }
        mock_response2 = Mock()
        mock_response2.json.return_value = {
            'results': [],
            'next': None
        }
        mock_safe_fetch.side_effect = [mock_response1, mock_response2]

        name, info = find_namespace(name='testns')
        assert name == 'testns'
        assert info['id'] == 1
        assert 'summary_fields' in info
        assert 'owners' in info['summary_fields']

    @patch('galaxy_ng.app.utils.galaxy.safe_fetch')
    def test_find_namespace_by_id(self, mock_safe_fetch):
        mock_response1 = Mock()
        mock_response1.json.return_value = {'id': 1, 'name': 'testns', 'summary_fields': {}}
        mock_response2 = Mock()
        mock_response2.json.return_value = {
            'results': [],
            'next': None
        }
        mock_safe_fetch.side_effect = [mock_response1, mock_response2]

        name, info = find_namespace(id=1)
        assert name == 'testns'
        assert info['id'] == 1


class TestGetNamespaceOwnersDetails(TestCase):

    @patch('galaxy_ng.app.utils.galaxy.safe_fetch')
    def test_get_namespace_owners_details_old_galaxy(self, mock_safe_fetch):
        mock_response = Mock()
        mock_response.json.return_value = {
            'results': [{'id': 1, 'username': 'user1'}],
            'next': None
        }
        mock_safe_fetch.return_value = mock_response

        owners = get_namespace_owners_details('http://example.com', 1)
        assert owners == [{'id': 1, 'username': 'user1'}]

    @patch('galaxy_ng.app.utils.galaxy.safe_fetch')
    def test_get_namespace_owners_details_new_galaxy(self, mock_safe_fetch):
        mock_response = Mock()
        mock_response.json.return_value = [{'id': 1, 'username': 'user1'}]
        mock_safe_fetch.return_value = mock_response

        owners = get_namespace_owners_details('http://example.com', 1)
        assert owners == [{'id': 1, 'username': 'user1'}]
