from unittest import mock
from uuid import uuid4

import pytest

from galaxy_ng.app.api.v1.models import LegacyNamespace, LegacyRole
from galaxy_ng.app.api.v1.serializers import (
    LegacyRoleRepositoryUpdateSerializer,
    LegacyRoleUpdateSerializer,
)

# Template syntax is blocked by Tier 2; nested repository.name is also Tier 1.
BLOCKED_BRANCH = 'release/{{region}}'
CHANGED_BLOCKED_BRANCH = 'release/{{other}}'
BLOCKED_USER = 'user-{{id}}'
CHANGED_BLOCKED_USER = 'user-{{other}}'
BLOCKED_REPO = 'role-{{env}}'
CHANGED_BLOCKED_REPO = 'role-{{other}}'
SAFE_REPO = 'ansible-role-docker'
NEW_SAFE_REPO = 'ansible-role-podman'
SAFE_USER = 'geerlingguy'
# Passes Tier 2 (no blocked patterns) but fails Tier 1 (/, (), '). Used to
# assert github_repo and repository.name share the same Tier 1 allowlist.
TIER1_ONLY_BLOCKED = "../x(y)'z"


@pytest.fixture
def enable_validation():
    # ENHANCED_INPUT_VALIDATION_ENABLED is dynaconf-backed here, so patch the
    # function CleanTextMixin actually calls rather than using override_settings.
    with mock.patch('ansible_base.lib.serializers.mixins.get_setting', return_value=True):
        yield


def _make_role(full_metadata, name='docker'):
    ns = LegacyNamespace.objects.create(name=f'ns-{uuid4().hex[:12]}')
    return LegacyRole.objects.create(
        namespace=ns, name=name, full_metadata=full_metadata,
    )


def _nested_field(role):
    parent = LegacyRoleUpdateSerializer(role, data={}, partial=True)
    return parent.fields['repository']


@pytest.mark.django_db
@pytest.mark.usefixtures('enable_validation')
class TestLegacyRoleUpdateGrandfathering:
    """Unchanged legacy metadata must not be re-rejected on update."""

    def test_full_put_repeating_stored_branch_while_changing_repo(self):
        role = _make_role({
            'github_user': SAFE_USER,
            'github_repo': SAFE_REPO,
            'github_branch': BLOCKED_BRANCH,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_user': SAFE_USER,
            'github_repo': NEW_SAFE_REPO,
            'github_branch': BLOCKED_BRANCH,
        })

        assert serializer.is_valid(), serializer.errors

    def test_unchanged_blocked_github_user_is_grandfathered(self):
        role = _make_role({
            'github_user': BLOCKED_USER,
            'github_repo': SAFE_REPO,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_user': BLOCKED_USER,
            'github_repo': NEW_SAFE_REPO,
        }, partial=True)

        assert serializer.is_valid(), serializer.errors

    def test_changed_blocked_github_user_is_rejected(self):
        role = _make_role({
            'github_user': BLOCKED_USER,
            'github_repo': SAFE_REPO,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_user': CHANGED_BLOCKED_USER,
        }, partial=True)

        assert not serializer.is_valid()
        assert 'github_user' in serializer.errors

    def test_unchanged_blocked_github_repo_is_grandfathered(self):
        role = _make_role({
            'github_user': SAFE_USER,
            'github_repo': BLOCKED_REPO,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_user': SAFE_USER,
            'github_repo': BLOCKED_REPO,
        }, partial=True)

        assert serializer.is_valid(), serializer.errors

    def test_changed_blocked_github_repo_is_rejected(self):
        role = _make_role({
            'github_user': SAFE_USER,
            'github_repo': BLOCKED_REPO,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_repo': CHANGED_BLOCKED_REPO,
        }, partial=True)

        assert not serializer.is_valid()
        assert 'github_repo' in serializer.errors

    def test_unchanged_blocked_github_branch_is_grandfathered(self):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'github_branch': BLOCKED_BRANCH,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_branch': BLOCKED_BRANCH,
        }, partial=True)

        assert serializer.is_valid(), serializer.errors

    def test_changed_blocked_github_branch_is_rejected(self):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'github_branch': BLOCKED_BRANCH,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_branch': CHANGED_BLOCKED_BRANCH,
        }, partial=True)

        assert not serializer.is_valid()
        assert 'github_branch' in serializer.errors

    def test_github_reference_only_metadata_grandfathers_github_branch(self):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'github_reference': BLOCKED_BRANCH,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_repo': NEW_SAFE_REPO,
            'github_branch': BLOCKED_BRANCH,
        }, partial=True)

        assert serializer.is_valid(), serializer.errors

    def test_github_reference_only_metadata_rejects_changed_branch(self):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'github_reference': BLOCKED_BRANCH,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_branch': CHANGED_BLOCKED_BRANCH,
        }, partial=True)

        assert not serializer.is_valid()
        assert 'github_branch' in serializer.errors

    @pytest.mark.parametrize('github_reference', [None, ''], ids=['null', 'empty'])
    def test_blank_github_reference_falls_back_to_stored_branch(self, github_reference):
        role = _make_role({
            'github_user': SAFE_USER,
            'github_repo': SAFE_REPO,
            'github_reference': github_reference,
            'github_branch': BLOCKED_BRANCH,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_repo': NEW_SAFE_REPO,
            'github_branch': BLOCKED_BRANCH,
        }, partial=True)

        assert serializer._is_unchanged('github_branch', BLOCKED_BRANCH) is True
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.parametrize('github_reference', [None, ''], ids=['null', 'empty'])
    def test_blank_github_reference_rejects_wrong_branch(self, github_reference):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'github_reference': github_reference,
            'github_branch': BLOCKED_BRANCH,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_branch': CHANGED_BLOCKED_BRANCH,
        }, partial=True)

        assert serializer._is_unchanged('github_branch', CHANGED_BLOCKED_BRANCH) is False
        assert not serializer.is_valid()
        assert 'github_branch' in serializer.errors

    @pytest.mark.parametrize('blank', [None, ''], ids=['null', 'empty'])
    def test_blank_github_reference_and_branch_does_not_grandfather_new_branch(self, blank):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'github_reference': blank,
            'github_branch': blank,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_repo': NEW_SAFE_REPO,
            'github_branch': BLOCKED_BRANCH,
        }, partial=True)

        assert serializer._is_unchanged('github_branch', BLOCKED_BRANCH) is False
        assert not serializer.is_valid()
        assert 'github_branch' in serializer.errors

    def test_create_without_instance_rejects_blocked_branch(self):
        serializer = LegacyRoleUpdateSerializer(data={
            'github_branch': BLOCKED_BRANCH,
        })

        assert not serializer.is_valid()
        assert 'github_branch' in serializer.errors

    def test_non_dict_full_metadata_does_not_raise_and_is_not_grandfathered(self):
        role = _make_role(['not-a-dict'])
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_branch': BLOCKED_BRANCH,
        }, partial=True)

        assert serializer._is_unchanged('github_branch', BLOCKED_BRANCH) is False
        assert not serializer.is_valid()
        assert 'github_branch' in serializer.errors

    def test_github_repo_and_repository_name_both_reject_tier1_only_payload(self):
        """github_repo is copied into repository.name; both must use Tier 1."""
        role = _make_role({
            'github_user': SAFE_USER,
            'github_repo': SAFE_REPO,
            'repository': {'name': SAFE_REPO, 'original_name': SAFE_REPO},
        })

        via_github_repo = LegacyRoleUpdateSerializer(role, data={
            'github_repo': TIER1_ONLY_BLOCKED,
        }, partial=True)
        assert not via_github_repo.is_valid()
        assert 'github_repo' in via_github_repo.errors

        via_repository_name = LegacyRoleUpdateSerializer(role, data={
            'repository': {'name': TIER1_ONLY_BLOCKED},
        }, partial=True)
        assert not via_repository_name.is_valid()
        assert 'name' in via_repository_name.errors.get('repository', {})


@pytest.mark.django_db
@pytest.mark.usefixtures('enable_validation')
class TestLegacyRoleRepositoryUpdateGrandfathering:
    """Nested repository fields read stored values from the parent role."""

    def test_unchanged_blocked_repository_name_is_grandfathered(self):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'repository': {'name': BLOCKED_REPO, 'original_name': SAFE_REPO},
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_repo': NEW_SAFE_REPO,
            'repository': {'name': BLOCKED_REPO},
        }, partial=True)

        assert serializer.is_valid(), serializer.errors

    def test_changed_blocked_repository_name_is_rejected(self):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'repository': {'name': BLOCKED_REPO, 'original_name': SAFE_REPO},
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'repository': {'name': CHANGED_BLOCKED_REPO},
        }, partial=True)

        assert not serializer.is_valid()
        assert 'name' in serializer.errors.get('repository', {})

    def test_unchanged_blocked_original_name_is_grandfathered(self):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'repository': {'name': SAFE_REPO, 'original_name': BLOCKED_REPO},
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_repo': NEW_SAFE_REPO,
            'repository': {'original_name': BLOCKED_REPO},
        }, partial=True)

        assert serializer.is_valid(), serializer.errors

    def test_changed_blocked_original_name_is_rejected(self):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'repository': {'name': SAFE_REPO, 'original_name': BLOCKED_REPO},
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'repository': {'original_name': CHANGED_BLOCKED_REPO},
        }, partial=True)

        assert not serializer.is_valid()
        assert 'original_name' in serializer.errors.get('repository', {})

    def test_nested_name_derived_from_top_level_github_repo_is_grandfathered(self):
        role = _make_role({
            'github_repo': BLOCKED_REPO,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'repository': {
                'name': BLOCKED_REPO,
                'original_name': BLOCKED_REPO,
            },
        }, partial=True)

        assert serializer.is_valid(), serializer.errors

    def test_nested_name_not_matching_github_repo_fallback_is_rejected(self):
        role = _make_role({
            'github_repo': BLOCKED_REPO,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'repository': {'name': CHANGED_BLOCKED_REPO},
        }, partial=True)

        assert not serializer.is_valid()
        assert 'name' in serializer.errors.get('repository', {})

    @pytest.mark.parametrize('repository', [None, 'not-a-dict', ['list']], ids=[
        'null', 'string', 'list',
    ])
    def test_malformed_repository_falls_back_to_github_repo(self, repository):
        role = _make_role({
            'github_repo': BLOCKED_REPO,
            'repository': repository,
        })
        nested = _nested_field(role)

        assert nested._is_unchanged('name', BLOCKED_REPO) is True
        assert nested._is_unchanged('original_name', BLOCKED_REPO) is True
        assert nested._is_unchanged('name', CHANGED_BLOCKED_REPO) is False

        serializer = LegacyRoleUpdateSerializer(role, data={
            'repository': {'name': BLOCKED_REPO, 'original_name': BLOCKED_REPO},
        }, partial=True)
        assert serializer.is_valid(), serializer.errors

    def test_missing_repository_falls_back_to_github_repo(self):
        role = _make_role({'github_repo': BLOCKED_REPO})
        nested = _nested_field(role)

        assert nested._is_unchanged('name', BLOCKED_REPO) is True
        assert nested._is_unchanged('original_name', BLOCKED_REPO) is True

    @pytest.mark.parametrize('blank', [None, ''], ids=['null', 'empty'])
    def test_blank_repository_names_fall_back_to_github_repo(self, blank):
        role = _make_role({
            'github_repo': BLOCKED_REPO,
            'repository': {'name': blank, 'original_name': blank},
        })
        nested = _nested_field(role)

        assert nested._is_unchanged('name', BLOCKED_REPO) is True
        assert nested._is_unchanged('original_name', BLOCKED_REPO) is True
        assert nested._is_unchanged('name', CHANGED_BLOCKED_REPO) is False
        assert nested._is_unchanged('original_name', CHANGED_BLOCKED_REPO) is False

        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_repo': NEW_SAFE_REPO,
            'repository': {'name': BLOCKED_REPO, 'original_name': BLOCKED_REPO},
        }, partial=True)
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.parametrize('blank', [None, ''], ids=['null', 'empty'])
    def test_blank_repository_name_does_not_grandfather_a_different_name(self, blank):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'repository': {'name': blank, 'original_name': BLOCKED_REPO},
        })
        nested = _nested_field(role)

        assert nested._is_unchanged('name', SAFE_REPO) is True
        assert nested._is_unchanged('original_name', BLOCKED_REPO) is True
        assert nested._is_unchanged('name', BLOCKED_REPO) is False

        serializer = LegacyRoleUpdateSerializer(role, data={
            'repository': {'name': BLOCKED_REPO, 'original_name': BLOCKED_REPO},
        }, partial=True)
        assert not serializer.is_valid()
        assert 'name' in serializer.errors.get('repository', {})

    @pytest.mark.parametrize('blank', [None, ''], ids=['null', 'empty'])
    def test_only_blank_nested_field_uses_github_repo_fallback(self, blank):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'repository': {'name': BLOCKED_REPO, 'original_name': blank},
        })
        nested = _nested_field(role)

        assert nested._is_unchanged('name', BLOCKED_REPO) is True
        assert nested._is_unchanged('original_name', SAFE_REPO) is True
        assert nested._is_unchanged('original_name', BLOCKED_REPO) is False

        serializer = LegacyRoleUpdateSerializer(role, data={
            'github_repo': NEW_SAFE_REPO,
            'repository': {'name': BLOCKED_REPO, 'original_name': SAFE_REPO},
        }, partial=True)
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.parametrize('repository', [None, 'not-a-dict', ['list']], ids=[
        'null', 'string', 'list',
    ])
    def test_malformed_repository_does_not_grandfather_unrelated_name(self, repository):
        role = _make_role({
            'github_repo': SAFE_REPO,
            'repository': repository,
        })
        serializer = LegacyRoleUpdateSerializer(role, data={
            'repository': {'name': BLOCKED_REPO},
        }, partial=True)

        assert _nested_field(role)._is_unchanged('name', BLOCKED_REPO) is False
        assert not serializer.is_valid()
        assert 'name' in serializer.errors.get('repository', {})

    def test_non_dict_full_metadata_on_nested_serializer_does_not_raise(self):
        role = _make_role(['not-a-dict'])
        nested = _nested_field(role)

        assert nested._is_unchanged('name', BLOCKED_REPO) is False

        serializer = LegacyRoleUpdateSerializer(role, data={
            'repository': {'name': BLOCKED_REPO},
        }, partial=True)
        assert not serializer.is_valid()
        assert 'name' in serializer.errors.get('repository', {})

    def test_nested_serializer_without_parent_instance_is_not_unchanged(self):
        serializer = LegacyRoleRepositoryUpdateSerializer(data={'name': BLOCKED_REPO})

        assert serializer._is_unchanged('name', BLOCKED_REPO) is False
        assert not serializer.is_valid()
        assert 'name' in serializer.errors
