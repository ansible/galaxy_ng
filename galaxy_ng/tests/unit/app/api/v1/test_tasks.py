import pytest

from unittest.mock import patch

from galaxy_importer.config import Config
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole

from galaxy_ng.app.api.v1.tasks import legacy_role_import
# from galaxy_ng.app.api.v1.tasks import legacy_sync_from_upstream


@pytest.mark.django_db
def test_legacy_role_import_simple():

    github_user = 'geerlingguy'
    github_repo = 'ansible-role-docker'
    alternate_role_name = 'docker'

    # make the legacy namespace
    legacy_ns, _ = LegacyNamespace.objects.get_or_create(name=github_user)

    # make the v3 namespace
    v3_ns, _ = Namespace.objects.get_or_create(name=github_user)

    # bind the namespaces
    legacy_ns.namespace = v3_ns
    legacy_ns.save()

    # delete any existing roles ...
    LegacyRole.objects.filter(namespace=legacy_ns, name=alternate_role_name).delete()

    # import it

    with patch('galaxy_ng.app.api.v1.tasks.Config', spec=Config) as MockConfig:

        MockConfig.return_value = Config()
        MockConfig.return_value.run_ansible_lint = False

        legacy_role_import(
            github_user=github_user,
            github_repo=github_repo,
            alternate_role_name=alternate_role_name
        )

    # find the role
    found = LegacyRole.objects.filter(namespace=legacy_ns, name=alternate_role_name)
    assert found.count() == 1
    role = found.first()

    # make sure the github_user is correct ...
    assert role.full_metadata.get('github_user') == github_user

    # make sure the github_repo is correct ...
    assert role.full_metadata.get('github_repo') == github_repo

    # should have used the default branch ..
    assert role.full_metadata.get('github_reference') == 'master'

    # should have many versions
    assert len(role.full_metadata['versions']) >= 1


@pytest.mark.django_db
def test_legacy_role_import_altered_github_org_name():

    namespace_name = 'painless'
    github_user = 'painless-software'
    github_repo = 'ansible-role-software'
    github_reference = 'main'
    alternate_role_name = 'software'

    # make the legacy namespace
    legacy_ns, _ = LegacyNamespace.objects.get_or_create(name=namespace_name)

    # make the v3 namespace
    v3_ns, _ = Namespace.objects.get_or_create(name=namespace_name)

    # bind the namespaces
    legacy_ns.namespace = v3_ns
    legacy_ns.save()

    # delete any existing roles ...
    LegacyRole.objects.filter(namespace=legacy_ns, name=alternate_role_name).delete()
    LegacyRole.objects.filter(
        full_metadata__github_user=github_user, name=alternate_role_name
    ).delete()

    # Make a role with the new info ..
    this_role, _ = LegacyRole.objects.get_or_create(namespace=legacy_ns, name=alternate_role_name)
    this_role.full_metadata['github_user'] = github_user
    this_role.full_metadata['github_repo'] = github_repo
    this_role.full_metadata['versions'] = [{'version': '0.0.1', 'name': 'v0.0.1'}]
    this_role.save()

    # import it
    with patch('galaxy_ng.app.api.v1.tasks.Config', spec=Config) as MockConfig:

        MockConfig.return_value = Config()
        MockConfig.return_value.run_ansible_lint = False

        legacy_role_import(
            github_user=github_user,
            github_repo=github_repo,
            github_reference=github_reference,
            alternate_role_name=alternate_role_name,
        )

    # find the role
    found = LegacyRole.objects.filter(
        full_metadata__github_user=github_user, name=alternate_role_name
    )
    assert found.count() == 1
    role = found.first()

    # make sure it's the right id
    assert role.id == this_role.id

    # make sure the name is correct ...
    assert role.name == alternate_role_name

    # make sure the github_user is correct ...
    assert role.full_metadata.get('github_user') == github_user
    assert role.full_metadata.get('github_repo') == github_repo

    # should have used the default branch ..
    assert role.full_metadata.get('github_reference') == github_reference
    assert role.full_metadata.get('github_branch') == github_reference

    # the old version isn't a tag so it should have been removed.
    assert role.full_metadata['versions'] == []


@pytest.mark.django_db
def test_legacy_role_import_with_tag_name():

    namespace_name = 'lablabs'
    github_user = 'lablabs'
    github_repo = 'ansible-role-rke2'
    github_reference = '1.24.0'
    alternate_role_name = 'rke2'

    # make the legacy namespace
    legacy_ns, _ = LegacyNamespace.objects.get_or_create(name=namespace_name)

    # make the v3 namespace
    v3_ns, _ = Namespace.objects.get_or_create(name=namespace_name)

    # bind the namespaces
    legacy_ns.namespace = v3_ns
    legacy_ns.save()

    # delete any existing roles ...
    LegacyRole.objects.filter(namespace=legacy_ns, name=alternate_role_name).delete()
    LegacyRole.objects.filter(
        full_metadata__github_user=github_user, name=alternate_role_name
    ).delete()

    # import it
    with patch('galaxy_ng.app.api.v1.tasks.Config', spec=Config) as MockConfig:

        MockConfig.return_value = Config()
        MockConfig.return_value.run_ansible_lint = False

        legacy_role_import(
            github_user=github_user,
            github_repo=github_repo,
            github_reference=github_reference,
            alternate_role_name=alternate_role_name,
        )

    # find the role
    found = LegacyRole.objects.filter(
        full_metadata__github_user=github_user, name=alternate_role_name
    )
    assert found.count() == 1
    role = found.first()

    # the branch and the reference should be the tag name ...
    assert role.full_metadata['github_reference'] == github_reference
    assert role.full_metadata['github_branch'] == github_reference

    # should have ALL the tag versions ...
    assert len(role.full_metadata['versions']) >= 1

    # the tag should be in the versions ...
    vmap = {x['version']: x for x in role.full_metadata['versions']}
    assert github_reference in vmap
